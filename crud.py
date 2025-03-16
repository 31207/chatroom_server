from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from models import User
from config import *
from auth import *
from jose import JWTError, jwt


# 创建用户
def create_user(db: Session, username: str, password: str):
    user = User(username=username, password=password, friends=[], friend_request=[], is_online=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# 查找用户
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_info(db: Session, token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        print(username)
        if username is None:
            return [None, {"error": "Invalid token"}]
        user = get_user_by_username(db, username)
        if user.token != token:
            return [None, {"error": "Invalid token"}]
        db.refresh(user)
        return [user,{"detail": "access"}]
    except JWTError:
        return [None, {"error": "Invalid token"}]


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def login(db: Session, username: str, password: str, token: str):
    user = get_user_by_username(db, username)
    if not user or user.password != password:
        return {"error": "Incorrect username or password"}
    # user.is_online = True
    if user.token != token or user.token == "":
        access_token = create_access_token(data={"sub": user.username},
                                           expires_delta=timedelta(minutes=TOKEN_EXPIRE_MINUTES))
        user.token = token = access_token
        db.commit()

    return {"token": token, "token_type": "bearer"}


def friend_request(db: Session, user_token: str, friend_name: str):
    user, result = get_user_info(db,user_token)
    if "error" in result:
        return result
    if user.username == friend_name:
        return {"error": "User and Friend can not be the same"}

    friend = get_user_by_username(db, friend_name)
    if not user or not friend:
        return {"error": "User or Friend not found"}
    if friend.id in user.friends:
        return {"error": "Already friends"}

    if user.id not in friend.friend_request:
        friend.friend_request.append(user.id)
        flag_modified(friend, "friend_request")

    db.commit()
    return {"message": "request sent"}


# agree添加好友
def accept_friend_request(db: Session, user_name: str, self_token: str):
    self, result = get_user_info(db, self_token)
    if "error" in result:
        return result
    user = get_user_by_username(db, user_name)
    if not user or not self:
        return {"error": "User or Friend not found"}
    if user.id not in self.friend_request:
        return {"error": "request not found"}
    if user.id not in self.friends:
        self.friends.append(user.id)
    if self.id not in user.friends:
        user.friends.append(self.id)

    self.friend_request.remove(user.id)
    flag_modified(user, "friends")
    flag_modified(self, "friends")
    flag_modified(self, "friend_request")
    db.commit()
    return {"message": "Friend added"}


# 删除好友
def remove_friend(db: Session, user_token: str, friend_name: str):
    user, result = get_user_info(db, user_token)
    if "error" in result:
        return result
    friend = get_user_by_username(db, friend_name)

    if not user or not friend:
        return {"error": "User or Friend not found"}

    if friend.id in user.friends:
        user.friends.remove(friend.id)
    if user.id in friend.friends:
        friend.friends.remove(user.id)
    flag_modified(user, "friends")
    flag_modified(friend, "friends")
    db.commit()
    return {"message": "Friend removed"}


# 获取好友列表
def get_friends(db: Session, user_token: str):
    user, result = get_user_info(db, user_token)
    if "error" in result:
        return result
    if not user:
        return {"error": "User not found"}
    friends = []
    for i in user.friends:
        tmp_user = get_user_by_id(db, i)
        friends.append(tmp_user.username)
    return friends
