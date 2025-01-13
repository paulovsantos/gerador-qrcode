import base64
from io import BytesIO
from django.shortcuts import get_object_or_404
from ninja import Router
import qrcode
from shortener.models import Clicks, Links
from shortener.schemas import LinkSchema, UpdateLinkSchema

shortener_router = Router()

@shortener_router.post('/', response={200: LinkSchema, 409: dict})
def create_shortener(request, link_schema: LinkSchema):
    data = link_schema.to_model_data()
    token = data['token']
    redirect_link = data['redirect_link']
    expiration_time = data['expiration_time']
    max_uniques_cliques = data['max_uniques_cliques']
    
    if token and Links.objects.filter(token=token).exists():
        return 409, {'error': 'Token já existe, use outro'}
    
    link = Links(
        redirect_link=redirect_link,
        token=token,
        expiration_time=expiration_time,
        max_uniques_cliques=max_uniques_cliques
    )
    link.save()
    
    return 200, LinkSchema.from_model(link)

@shortener_router.put("/{link_id}/", response={200: UpdateLinkSchema, 409: dict})
def update_link(request, link_id: int, link_schema: UpdateLinkSchema):
    link = get_object_or_404(Links, id=link_id)
    token = link_schema.dict()['token']
    if token and Links.objects.filter(token=token):
        return 409, {'error': 'Token já existe, use outro'}
 
    for field, value in link_schema.dict().items():
        if value is not None:
            setattr(link, field, value)
 
    link.save() 
    return 200, link

@shortener_router.get("statistics/{link_id}/", response={200: dict})
def statistics(request, link_id: int):
    link = get_object_or_404(Links, id=link_id)
    uniques_clicks = Clicks.objects.filter(link=link).values('ip').distinct().count()
    total_clicks = Clicks.objects.filter(link=link).values('ip').count()
    return 200, {'uniques_clicks': uniques_clicks, 'total_clicks': total_clicks}

def get_api_url(request, token):
    scheme = request.scheme 
    host = request.get_host()
    return f"{scheme}://{host}/api/{token}"

@shortener_router.get("qrcode/{link_id}/", response={200: dict})
def get_qrcode(request, link_id: int):
    link = get_object_or_404(Links, id=link_id)
    qr = qrcode.QRCode(
        version=1, 
        error_correction=qrcode.constants.ERROR_CORRECT_L, 
        box_size=10,
        border=4, 
    )
    print(get_api_url(request, link.token))
    qr.add_data(get_api_url(request, link.token))
    qr.make(fit=True)
    content = BytesIO()
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(content)
    data = base64.b64encode(content.getvalue()).decode('UTF-8')
    return 200, {'content_image': data}
