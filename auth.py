import jwt
import requests
from functools import wraps
from flask import request, jsonify, current_app
import os
from dotenv import load_dotenv

load_dotenv()

class ClerkAuth:
    def __init__(self):
        self.clerk_secret_key = os.getenv('CLERK_SECRET_KEY')
        self.clerk_publishable_key = os.getenv('CLERK_PUBLISHABLE_KEY')
        self.clerk_jwks_url = os.getenv('CLERK_JWKS_URL')
        self.clerk_domain = os.getenv('CLERK_DOMAIN', 'your-domain.clerk.accounts.dev')
        
        if not all([self.clerk_secret_key, self.clerk_publishable_key, self.clerk_jwks_url]):
            raise ValueError("Missing required Clerk environment variables")
    
    def verify_token(self, token):
        """Verify Clerk JWT token"""
        try:
       
            if token.startswith('Bearer '):
                token = token[7:]
            
           
            unverified_header = jwt.get_unverified_header(token)
           
            kid = unverified_header.get('kid')
            if not kid:
                return None, "No key ID in token"

            jwks_response = requests.get(self.clerk_jwks_url)
            jwks = jwks_response.json()
            
          
            key = None
            for jwk in jwks['keys']:
                if jwk['kid'] == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                    break
            
            if not key:
                return None, "Key not found"
            
           
            payload = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=self.clerk_publishable_key,
                issuer=f"https://clerk.{os.getenv('CLERK_DOMAIN', 'your-domain.clerk.accounts.dev')}"
            )
            
            return payload, None
            
        except jwt.ExpiredSignatureError:
            return None, "Token has expired"
        except jwt.InvalidTokenError as e:
            return None, f"Invalid token: {str(e)}"
        except Exception as e:
            return None, f"Token verification error: {str(e)}"
    
    def get_user_from_token(self, token):
        """Extract user information from verified token"""
        payload, error = self.verify_token(token)
        if error:
            return None, error
        
        user_info = {
            'user_id': payload.get('sub'),
            'email': payload.get('email'),
            'first_name': payload.get('given_name'),
            'last_name': payload.get('family_name'),
            'username': payload.get('preferred_username'),
            'session_id': payload.get('sid')
        }
        
        return user_info, None


clerk_auth = ClerkAuth()

def require_auth(f):
    """Decorator to require authentication for Flask routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
       
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header provided'}), 401
        
       
        user_info, error = clerk_auth.get_user_from_token(auth_header)
        if error:
            return jsonify({'error': error}), 401
        
       
        request.current_user = user_info
        return f(*args, **kwargs)
    
    return decorated_function

def optional_auth(f):
    """Decorator for optional authentication - doesn't fail if no token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header:
            user_info, error = clerk_auth.get_user_from_token(auth_header)
            if not error:
                request.current_user = user_info
            else:
                request.current_user = None
        else:
            request.current_user = None
        
        return f(*args, **kwargs)
    
    return decorated_function
