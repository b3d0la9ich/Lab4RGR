class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:4780@localhost/airport_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'super_secret_key_123'