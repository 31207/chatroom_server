from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import crud, models
import uvicorn
from pydantic import BaseModel
import asyncio
import json

models.Base.metadata.create_all(bind=engine)
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
# 存储连接的 WebSocket 客户端

class ClientsData:
    username: str
    token: str
    ws: WebSocket
class ConnectedClients:
    def __init__(self):
        self.clients = list()
    async def add(self, clientData: ClientsData):
        for i in range(len(self.clients)):
            if self.clients[i].username == clientData.username:
                raise Exception("重复登录")
        self.clients.append(clientData)

    async def remove(self, username):
        self.clients = [i for i in self.clients if i.username != username]

    async def broadcast(self, data: str):
        try:
            j = json.loads(data)
            username = j["username"]
            for i in self.clients:
                if i.username != username:
                    await i.ws.send_text(data)
        except Exception as e:
            print(e)
    def getCount(self):
        return len(self.clients)

connectedClients = ConnectedClients()

class LoginRequest(BaseModel):
    username: str
    password: str
    token: str = ""


class RegisterRequest(BaseModel):
    username: str
    password: str


class GetUserInfoRequest(BaseModel):
    token: str


class FriendRequest(BaseModel):
    token: str
    friend_name: str


class AcceptFriendRequest(BaseModel):
    self_token: str
    user_name: str


class RemoveFriendRequest(BaseModel):
    token: str
    friend_name: str


class GetFriendsRequest(BaseModel):
    token: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# WebSocket 路由
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    print(ws.headers)
    try:
        jdata = ws.headers.get("Authorization")
        print(jdata)
        j = json.loads(jdata)
        username = j['username']
        token = j['token']
        client_data = ClientsData()
        client_data.username = username
        client_data.token = token
        if username != "" and token != "":
            db = SessionLocal()
            user, result = crud.get_user_info(db, token)
            if "error" in result:
                raise Exception("Invalid token")
            if not user:
                raise Exception("Username not found")

            client_data.ws = ws
            await connectedClients.add(client_data)

            await ws.accept()
        while True:
            data = await ws.receive_text()
            print(data)
            # 广播消息给所有客户端
            await connectedClients.broadcast(data)
    except WebSocketDisconnect as err:
        await connectedClients.remove(username)
        print("disconnected:", err, "count:", connectedClients.getCount())
    except Exception as err:
        await ws.close(code=1008,reason=str(err))
        print("error occur:", err, "count:", connectedClients.getCount())

@app.post("/register/")
def _(args: RegisterRequest, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, args.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db, args.username, args.password)


@app.post("/login/")
def _(args: LoginRequest, db: Session = Depends(get_db)):
    result = crud.login(db, args.username, args.password, args.token)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/get_user_info/")
def _(args: GetUserInfoRequest, db: Session = Depends(get_db)):
    user, result = crud.get_user_info(db, args.token)
    if "error" in result:
        raise HTTPException(status_code=400, detail="Invalid token")
    if not user:
        raise HTTPException(status_code=400, detail="Username not found")
    return user


@app.post("/friend_request/")
def _(args: FriendRequest, db: Session = Depends(get_db)):
    result = crud.friend_request(db, args.token, args.friend_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/accept_friend_request/")
def _(args: AcceptFriendRequest, db: Session = Depends(get_db)):
    result = crud.accept_friend_request(db, args.user_name, args.self_token)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.delete("/remove_friend/")
def _(args: RemoveFriendRequest, db: Session = Depends(get_db)):
    result = crud.remove_friend(db, args.token, args.friend_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/get_friends/")
def _(args: GetFriendsRequest, db: Session = Depends(get_db)):
    friends = crud.get_friends(db, args.token)
    if "error" in friends:
        raise HTTPException(status_code=400, detail=friends["error"])
    return {"friends": friends}



if __name__ == "__main__":
    uvicorn.run(app,host="0.0.0.0", port=8080, log_level="info")
