import base64
import json
from openai import OpenAI
from pathlib import Path
import sys
from io import BytesIO
from PIL import Image

class InvitationExtractor:
    def __init__(self, api_key=None):
        """
        Initialize the invitation extractor
        
        Args:
            api_key (str): OpenAI API key. If None, will use OPENAI_API_KEY environment variable
        """
        self.client = OpenAI(api_key=api_key)
    
    def encode_image_from_path(self, image_path):
        """Encode image from file path to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def encode_image_from_bytes(self, image_bytes):
        """Encode image from bytes to base64"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def encode_image_from_pil(self, pil_image):
        """Encode PIL Image to base64"""
        buffer = BytesIO()
        # Save as JPEG if no format specified
        format = pil_image.format or 'JPEG'
        pil_image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def extract_invitation_info(self, image_input, model="gpt-4o"):
        """
        Extract structured information from an invitation image
        
        Args:
            image_input: Can be:
                - str: Path to image file
                - bytes: Raw image bytes
                - PIL.Image: PIL Image object
                - BytesIO: BytesIO object containing image data
            model (str): OpenAI model to use (default: gpt-4o)
            
        Returns:
            dict: Structured invitation information
        """
        # Handle different input types
        if isinstance(image_input, str):
            # File path
            base64_image = self.encode_image_from_path(image_input)
        elif isinstance(image_input, bytes):
            # Raw bytes
            base64_image = self.encode_image_from_bytes(image_input)
        elif isinstance(image_input, Image.Image):
            # PIL Image
            base64_image = self.encode_image_from_pil(image_input)
        elif isinstance(image_input, BytesIO):
            # BytesIO object
            image_input.seek(0)  # Reset position
            base64_image = self.encode_image_from_bytes(image_input.read())
        else:
            raise ValueError("Unsupported image input type. Use file path (str), bytes, PIL Image, or BytesIO")
        
        # Create the prompt for structured extraction
        prompt = """
        Analyze this invitation image and extract the following information in JSON format:
        
        {
            "event_title": "The main title or name of the event",
            "date": "Event date (format as YYYY-MM-DD if possible, otherwise as written)",
            "time": "Event time (if specified)",
            "location": {
                "venue": "Name of the venue/place",
                "address": "Full address if available",
                "city": "City",
                "state": "State/Province",
                "country": "Country (if specified)"
            },
            "description": "Event description or additional details",
            "host": "Who is hosting/organizing the event",
            "dress_code": "Dress code if mentioned",
            "rsvp": {
                "required": true/false,
                "contact": "RSVP contact information",
                "deadline": "RSVP deadline if specified"
            },
            "additional_info": "Any other relevant information (parking, gifts, special instructions, etc.)"
        }
        
        If any information is not available in the image, use null for that field.
        Only extract information that is clearly visible in the invitation.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.1  # Low temperature for more consistent extraction
            )
            
            # Extract the JSON response
            content = response.choices[0].message.content
            
            # Try to parse as JSON
            try:
                # Look for JSON in the response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, return raw content
                return {"raw_response": content, "error": "Could not parse as JSON"}
                
        except Exception as e:
            return {"error": f"API call failed: {str(e)}"}

def main():
    """Command line interface"""
    if len(sys.argv) != 2:
        print("Usage: python invitation_ocr.py <image_path>")
        print("Make sure to set your OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Check if image exists
    if not Path(image_path).exists():
        print(f"Error: Image file '{image_path}' not found")
        sys.exit(1)
    
    # Create extractor and process image
    extractor = InvitationExtractor()
    result = extractor.extract_invitation_info(image_path)
    
    # Pretty print the result
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

# Example usage as a module:
"""
from invitation_ocr import InvitationExtractor
from PIL import Image
from io import BytesIO

# Initialize with API key
extractor = InvitationExtractor(api_key="your-openai-api-key")

# Method 1: From file path
result = extractor.extract_invitation_info("path/to/invitation.jpg")

# Method 2: From decrypted bytes (your use case)
decrypted_bytes = b"..."  # your decrypted image bytes
result = extractor.extract_invitation_info(decrypted_bytes)

# Method 3: From PIL Image (your specific case)
pil_image = Image.open(BytesIO(decrypted))
result = extractor.extract_invitation_info(pil_image)

# Method 4: From BytesIO directly
bio = BytesIO(decrypted)
result = extractor.extract_invitation_info(bio)

# Access specific information
print(f"Event: {result.get('event_title')}")
print(f"Date: {result.get('date')}")
print(f"Location: {result.get('location', {}).get('venue')}")
"""