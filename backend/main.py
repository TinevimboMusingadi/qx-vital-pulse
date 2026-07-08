import os
import json
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import uuid
import torch
from huggingface_hub import hf_hub_download
import joblib

# Import the load_model function from the real modeling_airs.py
from modeling_airs import load_model

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="AIRS Sprint 1 - Respiratory Disease Classifier API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global memory cache for loaded models and scalers
# Format: { "model_id": { "model": PyTorchModel, "config": dict, "scaler": StandardScaler } }
model_cache = {}

HF_TOKEN = os.environ.get("HF_TOKEN")
REPO_ID = "Quantilytix/airs-sprint1-models"

# Available models mapping frontend ID to huggingface path
MODEL_PATHS = {
    "exp1-tabular-attention": "exp1-tabular-attention/fold-0",
    "exp2-acoustic-both": "exp2-acoustic-both/fold-0",
    "exp4-encoder-free-unified": "exp4-encoder-free-unified/fold-0"
}

def get_or_load_model(model_id: str):
    """Dynamically downloads and loads the model and scaler from HF, caching it in memory."""
    if model_id not in MODEL_PATHS:
        raise ValueError(f"Unknown model_id: {model_id}")
        
    if model_id in model_cache:
        return model_cache[model_id]
        
    base_path = MODEL_PATHS[model_id]
    
    print(f"Downloading {model_id} from Hugging Face...")
    try:
        local_config = hf_hub_download(repo_id=REPO_ID, filename=f"{base_path}/config.json", token=HF_TOKEN)
        local_weights = hf_hub_download(repo_id=REPO_ID, filename=f"{base_path}/pytorch_model.bin", token=HF_TOKEN)
        
        # Load the actual PyTorch architecture
        model, config = load_model(local_config, local_weights, map_location="cpu")
        model.eval() # Set to evaluation mode
        
        # Try to load the tabular scaler if it exists
        scaler = None
        try:
            local_scaler = hf_hub_download(repo_id=REPO_ID, filename=f"{base_path}/tab_scaler.joblib", token=HF_TOKEN)
            scaler = joblib.load(local_scaler)
        except Exception as e:
            print(f"Warning: No tab_scaler.joblib found for {model_id} or failed to load: {e}")
            
        print(f"Successfully loaded {config['model_class']} and scaler!")
        
        # Cache it
        model_cache[model_id] = {
            "model": model,
            "config": config,
            "scaler": scaler
        }
        return model_cache[model_id]
        
    except Exception as e:
        print(f"Error loading model {model_id}: {e}")
        raise e


@app.get("/")
def read_root():
    return {"message": "Welcome to the AIRS Respiratory Classification API"}

@app.post("/predict")
async def predict(
    audio: UploadFile = File(None),
    model_id: str = Form(default="exp4-encoder-free-unified"),
    # The 9 Exact Features
    age: float = Form(default=0.0),
    gender: str = Form(default="unknown"),
    tbContactHistory: bool = Form(default=False),
    wheezingHistory: bool = Form(default=False),
    phlegmCough: bool = Form(default=False),
    familyAsthmaHistory: bool = Form(default=False),
    feverHistory: bool = Form(default=False),
    coldPresent: bool = Form(default=False),
    packYears: float = Form(default=0.0)
):
    """
    Endpoint to receive audio and 9 precise tabular features for prediction.
    """
    try:
        model_data = get_or_load_model(model_id)
        model = model_data["model"]
        config = model_data["config"]
        scaler = model_data["scaler"]
    except Exception as e:
        return {"error": f"Failed to load model {model_id}: {str(e)}"}

    cough_wav = None
    temp_filename = None
    
    if audio is not None and audio.filename:
        file_extension = audio.filename.split(".")[-1]
        temp_filename = f"{uuid.uuid4()}.{file_extension}"
        
        with open(temp_filename, "wb") as f:
            f.write(await audio.read())
            
        try:
            # Safely process audio to prevent crashes on large files
            import wave
            import numpy as np
            
            with wave.open(temp_filename, 'rb') as f:
                # Limit to first 10 seconds of audio to prevent OOM
                sr = f.getframerate()
                max_frames = sr * 10
                n_frames = min(f.getnframes(), max_frames)
                frames = f.readframes(n_frames)
                
                waveform = torch.from_numpy(np.frombuffer(frames, dtype=np.int16)).float()
                waveform = waveform / 32768.0
                
                if f.getnchannels() > 1:
                    waveform = waveform.view(-1, f.getnchannels())
                    waveform = torch.mean(waveform, dim=1)
                    
                waveform = waveform.unsqueeze(0) # add batch dimension: (1, T)
                cough_wav = waveform
        except Exception as e:
            print(f"Audio processing error: {e}")
            # If audio fails, we still try to proceed with tabular only if the model supports it
            pass

    # Process 9 Tabular Features exactly as Notebook did
    # Order: ['age', 'gender', 'tbContactHistory', 'wheezingHistory', 'phlegmCough', 'familyAsthmaHistory', 'feverHistory', 'coldPresent', 'packYears']
    
    gender_num = 1.0 if gender.lower() == "female" else 0.0
    
    tab_raw = [
        float(age),
        float(gender_num),
        float(tbContactHistory),
        float(wheezingHistory),
        float(phlegmCough),
        float(familyAsthmaHistory),
        float(feverHistory),
        float(coldPresent),
        float(packYears)
    ]
    
    # Scale 'age' and 'packYears' (indices 0 and 8)
    if scaler is not None:
        try:
            import numpy as np
            # Try to scale using the loaded scaler. Note: The saved joblib might be a Pipeline 
            # expecting more features. If so, it will raise ValueError.
            cont_features = np.array([[tab_raw[0], tab_raw[8]]])
            scaled_cont = scaler.transform(cont_features)[0]
            tab_raw[0] = scaled_cont[0]
            tab_raw[8] = scaled_cont[1]
        except Exception as e:
            print(f"Scaler failed, falling back to manual normalization: {e}")
            tab_raw[0] = float(age) / 100.0
            tab_raw[8] = float(packYears) / 100.0
    else:
        tab_raw[0] = float(age) / 100.0
        tab_raw[8] = float(packYears) / 100.0
        
    tab_features = torch.tensor([tab_raw], dtype=torch.float32)

    try:
        with torch.no_grad():
            if config["model_class"] in ["TabularAttentionModel"]:
                logits = model(tab_features)
            elif config["model_class"] in ["EncoderFreeUnifiedModel", "LateFusionClassical"]:
                logits = model(tab=tab_features, cough_wav=cough_wav)
            else:
                # Fallback guess
                logits = model(tab_features)
                
            probs = torch.nn.functional.softmax(logits, dim=-1)
            # NUM_CLASSES = 3. Class 0: Healthy, 1: Disease A, 2: Disease B
            prob_disease = (probs[0, 1] + probs[0, 2]).item()

    except Exception as e:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"error": f"Inference Error: {str(e)}"}

    # Clean up
    if temp_filename and os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    return {
        "status": "success",
        "filename": audio.filename if audio else None,
        "prediction": {
            "disease_probability": prob_disease,
            "diagnosis": "Positive" if prob_disease > 0.5 else "Negative",
            "confidence": "High" if max(prob_disease, 1 - prob_disease) > 0.8 else "Medium",
            "model_version": config["model_class"],
            "model_id": model_id
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
