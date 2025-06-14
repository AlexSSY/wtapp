from contextlib import asynccontextmanager
from typing import Type
from fastapi import Request, FastAPI, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from wtforms import Form, ValidationError, validators, StringField, IntegerField
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapper, DeclarativeBase, Session

from db import SessionLocal, engine, Base


def get_db():
    db = SessionLocal()
    try:
        yield db
    except:
        db.close()


def Unique(model, field_name: str, session_getter):
    """
    Проверяет, что значение уникально в модели.
    
    :param model: SQLAlchemy модель (например, User)
    :param field_name: строка, имя столбца (например, 'email')
    :param session_getter: функция, возвращающая активную сессию (Session)
    """
    def _validate(form, field):
        session = session_getter()
        value = field.data

        if value is None:
            return  # можно не проверять null

        column = getattr(model, field_name)
        exists = session.query(model).filter(column == value).first()

        if exists:
            raise ValidationError(f"{field.label.text} должен быть уникальным.")

    return _validate


def form_for_model(model: Type[DeclarativeBase]) -> Type[Form]:
    mapper: Mapper = model.__mapper__
    fields = {}

    for column in mapper.columns:
        name = column.key
        type_ = column.type
        is_required = not column.nullable and not column.default and not column.primary_key
        is_unique = column.unique or False

        # Пропустим id-поле
        if column.primary_key:
            continue

        _validators = []
        if is_required:
            _validators.append(validators.DataRequired())

        if is_unique:
            _validators.append(Unique(model, name, lambda: next(get_db())))

        if isinstance(type_, String):
            if type_.length:
                _validators.append(validators.Length(max=type_.length))
            fields[name] = StringField(name.capitalize(), validators=_validators)

        elif isinstance(type_, Integer):
            fields[name] = IntegerField(name.capitalize(), validators=_validators)

        # Можно добавить больше типов (Boolean, Float и т.д.)

    return type(f"{model.__name__}Form", (Form,), fields)


class Color(Base):
    __tablename__ = "colors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)


class Flower(Base):
    __tablename__ = "flowers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    color_id = Column(Integer, ForeignKey('colors.id'), nullable=False)


templating = Jinja2Templates('templates')


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)


models = {
    'Color': Color,
    'Flower': Flower,
}


@app.get('/')
def home(request: Request):
    return templating.TemplateResponse(request, 'home.html', {'models': models.keys()})


@app.get('/favicon.ico')
def x():
    return ''


@app.get('/{model_class_name}')
def new(request: Request, model_class_name: str):
    model_class = models.get(model_class_name)
    form = form_for_model(model_class)()
    return templating.TemplateResponse(request, 'form.html', {'form': form})


@app.post('/{model_class_name}')
async def create(request: Request, model_class_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    model_class = models.get(model_class_name)
    form = form_for_model(model_class)(formdata=form_data)
    if form.validate():
        model_instance = model_class(**form.data)
        db.add(model_instance)
        db.commit()
        return RedirectResponse('/', status_code=301)
    else:
        return templating.TemplateResponse(request, 'form.html', {'form': form})
