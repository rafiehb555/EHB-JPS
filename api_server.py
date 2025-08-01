import datetime
import hashlib
import os
import jwt
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from auth_manager import AuthManager
from data_processor import DataProcessor
from database import db

#!/usr/bin/env python3
"""
EHB-5 API Server
RESTful API endpoints for the EHB-5 project
"""


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ehb5-secret-key-2024')
CORS(app)

# Initialize managers
auth_manager = AuthManager()
data_processor = DataProcessor()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/auth/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Create user
        if db.create_user(username, email, password_hash):
            return jsonify({'message': 'User registered successfully'}), 201
        else:
            return jsonify({'error': 'User already exists'}), 409

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not all([username, password]):
            return jsonify({'error': 'Missing credentials'}), 400

        # Verify user
        user = auth_manager.authenticate_user(username, password)
        if user:
            # Generate JWT token
            token = auth_manager.generate_token(user['id'], user['username'])
            return jsonify({
                'message': 'Login successful',
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role']
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users', methods=['GET'])
@auth_manager.require_auth
def get_users():
    """Get all users (admin only)"""
    try:
        users = db.get_all_users()
        return jsonify({
            'users': users,
            'total': len(users)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['GET'])
@auth_manager.require_auth
def get_user(user_id):
    """Get specific user by ID"""
    try:
        user = db.get_user_by_id(user_id)
        if user:
            return jsonify(user), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects', methods=['GET'])
@auth_manager.require_auth
def get_projects():
    """Get all projects"""
    try:
        projects = db.get_all_projects()
        return jsonify({
            'projects': projects,
            'count': len(projects)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects', methods=['POST'])
@auth_manager.require_auth
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')

        if not name:
            return jsonify({'error': 'Project name is required'}), 400

        user_id = session.get('user_id')
        if db.create_project(name, description, user_id):
            return jsonify({'message': 'Project created successfully'}), 201
        else:
            return jsonify({'error': 'Failed to create project'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/files', methods=['GET'])
@auth_manager.require_auth
def get_data_files():
    """Get all data files"""
    try:
        project_id = request.args.get('project_id', type=int)
        files = db.get_data_files(project_id)
        return jsonify({
            'files': files,
            'count': len(files)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/files', methods=['POST'])
@auth_manager.require_auth
def upload_data_file():
    """Upload a data file"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        file_type = data.get('file_type')
        content = data.get('content')
        project_id = data.get('project_id')

        if not all([filename, file_type, content]):
            return jsonify({'error': 'Missing required fields'}), 400

        user_id = session.get('user_id')
        if db.save_data_file(
            filename,
            file_type,
            content,
            project_id,
            user_id):
            return jsonify({'message': 'File uploaded successfully'}), 201
        else:
            return jsonify({'error': 'Failed to upload file'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/process', methods=['POST'])
@auth_manager.require_auth
def process_data():
    """Process data using the data processor"""
    try:
        data = request.get_json()
        input_data = data.get('data')
        operation = data.get('operation', 'analyze')

        if not input_data:
            return jsonify({'error': 'No data provided'}), 400

        # Process data
        result = data_processor.process_data(input_data, operation)

        return jsonify({
            'result': result,
            'operation': operation,
            'processed_at': datetime.datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """Get system status"""
    try:
        # Get database status
        projects_count = len(db.get_all_projects())
        files_count = len(db.get_data_files())

        return jsonify({
            'status': 'operational',
            'database': 'connected',
            'api': 'active',
            'debug': False,
            'stats': {
                'projects': projects_count,
                'files': files_count,
                'users': 1  # Placeholder
            },
            'timestamp': datetime.datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500


@app.route('/api/system/logs', methods=['GET'])
@auth_manager.require_auth
def get_system_logs():
    """Get system logs"""
    try:
        # This would typically get logs from the database
        logs = [
            {
                'id': 1,
                'level': 'INFO',
                'message': 'System initialized',
                'timestamp': datetime.datetime.now().isoformat()
            }
        ]

        return jsonify({
            'logs': logs,
            'count': len(logs)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting EHB-5 API Server...")
    print("📊 API URL: http://localhost:5000")
    print("📚 API Documentation: http://localhost:5000/api/health")


# Global error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad Request',
        'message': 'Invalid request data',
        'status_code': 400
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Authentication required',
        'status_code': 401
    }), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({
        'error': 'Forbidden',
        'message': 'Access denied',
        'status_code': 403
    }), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Resource not found',
        'status_code': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'status_code': 500
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    return jsonify({
        'error': 'Server Error',
        'message': str(error),
        'status_code': 500
    }), 500

# Custom error handling decorator
def handle_errors(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'Operation Failed',
                'message': str(e),
                'status_code': 500
            }), 500
    wrapper.__name__ = f.__name__
    return wrapper


    # Log system startup
    db.log_system_event('INFO', 'API Server started')

    app.run(host='0.0.0.0', port=5000, debug=True)
