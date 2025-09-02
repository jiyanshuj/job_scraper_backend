class ValidationService:
    @staticmethod
    def validate_job_data(job_data):
        # Implement validation logic for job data
        # For example, check required fields, data types, etc.
        required_fields = ['job_title', 'job_link', 'company_name']
        for field in required_fields:
            if field not in job_data or not job_data[field]:
                return False, f"Missing required field: {field}"
        return True, "Valid data"
