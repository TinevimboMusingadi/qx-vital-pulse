import React from 'react';

const DataForm = ({ formData, setFormData }) => {
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <div className="data-form">
      <div className="form-group">
        <label htmlFor="age">Age</label>
        <input
          type="number"
          id="age"
          name="age"
          min="0"
          max="120"
          value={formData.age}
          onChange={handleChange}
          placeholder="e.g. 45"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="gender">Gender</label>
        <select
          id="gender"
          name="gender"
          value={formData.gender}
          onChange={handleChange}
          required
        >
          <option value="">Select gender...</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="symptoms">Symptoms (Comma separated)</label>
        <input
          type="text"
          id="symptoms"
          name="symptoms"
          value={formData.symptoms}
          onChange={handleChange}
          placeholder="e.g. cough, fever, shortness of breath"
        />
      </div>
    </div>
  );
};

export default DataForm;
