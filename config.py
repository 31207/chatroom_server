import yaml
with open("config.yaml", "r", encoding="utf-8") as file:
    data = yaml.safe_load(file)

SECRET_KEY = data["SECRET_KEY"]
ALGORITHM = data["ALGORITHM"]
TOKEN_EXPIRE_MINUTES = data["TOKEN_EXPIRE_MINUTES"]
DATABASE_URL = data["DATABASE_URL"]