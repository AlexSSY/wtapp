from fastapi import Request, FastAPI
from fastapi.templating import Jinja2Templates
from wtforms import Form, validators, StringField


templating = Jinja2Templates('templates')
app = FastAPI()


class MyForm(Form):
    first_name = StringField('First Name', validators=[validators.input_required()])
    last_name  = StringField('Last Name', validators=[validators.optional()])


@app.get('/')
def home(request: Request):
    form = MyForm()
    form.__str__()
    return templating.TemplateResponse(request, 'home.html')
