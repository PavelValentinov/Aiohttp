from datetime import datetime
from urllib import request

import pydantic
import hashlib
import asyncpg
from gino import Gino
from aiohttp import web

PG_DSN = f'postgres://postgres:-@127.0.0.1:5432/ads'
headers = {'Content-type': 'application/json',  # Определение типа данных
           'Accept': 'text/plain',
           'Content-Encoding': 'utf-8'}

@web.middleware
async def validation_error_handler(request, handler):
    try:
        response = await handler(request)
    except pydantic.error_wrappers.ValidationError as er:
        response = web.json_response({'error': str(er)}, status=400)
    return response

app = web.Application(middlewares=[validation_error_handler])
db = Gino()


class ModelMixin:

    @classmethod
    async def create_instance(cls, *args, **kwargs):
        try:
            return (await cls.create(*args, **kwargs))
        except asyncpg.exceptions.UniqueViolationError:
            raise web.HTTPBadRequest


class UserModel(db.Model, ModelMixin):
    # table user
    __tablename__  = 'user_ads'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    email = db.Column(db.String(), nullable=False)
    password = db.Column(db.String(), nullable=False)

    def __repr__(self):
        return f'User({self.id}, {self.name})'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'password': self.password
        }



    @classmethod
    async def create_instance(cls, *args, **kwargs):
        kwargs['password'] = hashlib.md5(kwargs['password'].encode()).hexdigest()
        return (await super().create_instance(*args, **kwargs))

    def to_dict(self):
        user_data = super().to_dict()
        user_data.pop('password')
        return user_data



class AdsModel(db.Model):
    # table ads
    __tablename__  = 'ads'
    id = db.Column(db.Integer(), primary_key=True)
    ads_name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    date_create = db.Column(db.DateTime, default=datetime.utcnow())
    id_owner = db.Column(db.Integer, db.ForeignKey('user_ads.id'), nullable=False)

    _idx1 = db.Index('app_users_username', 'ads_name', unique=True)

    def __repr__(self):
        return f'Ads({self.id}, {self.description})'

    def to_dict(self):
        return {
            'id': self.id,
            'ads_name': self.ads_name,
            'description': self.description,
            'date_create': str(self.date_create),
            'id_owner': self.id_owner
        }


class User(web.View):

    async def post(self):
        user_data = await self.request.json(headers)
        print(user_data)
        user_serialized = UserSerializer(**user_data)
        user_data = user_serialized.dict()
        new_user = await UserModel.create_instance(**user_data)
        return web.json_response(new_user.to_dict())


    async def get(self):
        user_id = self.request.match_info['user_id']
        user = await UserModel.get(int(user_id))
        user_data = user.to_dict()
        return web.json_response(user_data)


class UserSerializer(pydantic.BaseModel):
    name: str
    email: str



class Ads(web.View):

    async def post(self):
        ads_data = await request.json()

        user = await User.get(int(ads_data['id_owner']))
        if user is None:
            return web.json_response({'error': 'Not Found Owner'}, status=404)

        ads_serialized = AdsSerializer(**ads_data)
        ads_data = ads_serialized.dict()
        new_ads = await AdsModel.create(**ads_data)
        # new_ads = await AdsModel.create(ads_name=ads_data['sdf'], description=ads_data['sdfsd'], id_owner=ads_data['1'])
        return web.json_response(new_ads.to_dict(), status=200)


    async def get(self):
        ads_id = self.request.match_info['ads_id']
        ads = await AdsModel.get(int(ads_id))
        if ads is None:
            return web.json_response({'error': 'Not found ads'}, status=404)
        else:
            ads_data = ads.to_dict()
            return web.json_response(ads_data)


    async def delete(self):
        ads_id = self.request.match_info['ads_id']
        ads = await AdsModel.get(int(ads_id))
        if ads is None:
            return web.json_response({'error': 'Not found ads'}, status=404)
        else:
            await ads.delete()

            return web.json_response({}, status=200)

    async def put(self):
        ads_id = self.request.match_info['ads_id']
        ads = await AdsModel.get(int(ads_id))
        if ads is None:
            return web.json_response({'error': 'Not found ads'}, status=404)
        else:
            ads_data = await request.json()
            await ads.update(title=ads_data['ads_name'], text=ads_data['description'], id_owner=ads_data['id_owner']).apply()

            return web.json_response({}, status=200)


class AdsSerializer(pydantic.BaseModel):
    ads_name: str
    description: str
    id_owner: int


async def init_orm(app):
    print('приложение стартовало')

    await db.set_bind(PG_DSN)
    await db.gino.create_all()
    yield
    await db.pop_bind().close()


app.add_routes([web.get('/ads/', Ads)])
app.add_routes([web.get('/ads/{ads_id:\d+}', Ads)])

app.add_routes([web.post('/ads/', Ads)])
app.add_routes([web.put('/ads/{ads_id:\d+}', Ads)])
app.add_routes([web.delete('/ads_del/{ads_id:\d+}', Ads)])

app.cleanup_ctx.append(init_orm)

web.run_app(app, port=8080)
