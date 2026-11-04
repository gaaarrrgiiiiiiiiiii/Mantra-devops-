"""Generate small representative documents; no private production data is used."""
from io import BytesIO

import pytest

TEXT = 'Pump P-205B bearing failure requires lubrication inspection.'


def payload_for(kind):
    stream = BytesIO()
    if kind == 'pdf':
        import fitz
        with fitz.open() as document:
            document.new_page().insert_text((50, 50), TEXT)
            return document.tobytes()
    if kind == 'docx':
        from docx import Document
        document = Document()
        document.add_paragraph(TEXT)
        document.save(stream)
    elif kind == 'xlsx':
        from openpyxl import Workbook
        book = Workbook()
        book.active.append([TEXT])
        book.save(stream)
    elif kind == 'pptx':
        from pptx import Presentation
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = TEXT
        presentation.save(stream)
    else:
        return TEXT.encode()
    return stream.getvalue()


@pytest.mark.parametrize('kind', ['txt', 'md', 'csv', 'eml', 'pdf', 'docx', 'xlsx', 'pptx'])
def test_representative_document_formats(client, monkeypatch, kind):
    monkeypatch.setattr(client.app.state.ingestion.settings, 'max_upload_bytes', 10 * 1024 * 1024)
    payload = payload_for(kind)
    response = client.post('/api/documents/upload', files={'file': ('fixture.' + kind, payload, 'application/octet-stream')})
    assert response.status_code == 200, response.text
    document = response.json()
    assert 'bearing failure' in ' '.join(chunk['content'] for chunk in document['chunks']).lower()
    assert client.get('/api/documents/' + document['id'] + '/raw').content == payload


def test_ingestion_failure_can_be_reprocessed_after_parser_recovery(client, monkeypatch):
    from app.services.parsers import DocumentParseError
    parser = client.app.state.ingestion.parser
    original = parser.parse

    def fail_once(*args, **kwargs):
        raise DocumentParseError('Simulated parser outage')

    monkeypatch.setattr(parser, 'parse', fail_once)
    response = client.post('/api/documents/upload', files={'file': ('recover.txt', TEXT.encode(), 'text/plain')})
    assert response.status_code == 422
    failures = client.get('/api/admin/ingestion-failures').json()
    assert len(failures) == 1 and failures[0]['attempts'] == 1
    failure_id = failures[0]['id']
    monkeypatch.setattr(parser, 'parse', original)
    retry = client.post('/api/admin/ingestion-failures/' + failure_id + '/reprocess')
    assert retry.status_code == 200 and retry.json()['status'] == 'indexed'
    assert client.get('/api/admin/ingestion-failures').json() == []
    assert len(client.get('/api/documents').json()) == 1


def test_image_ocr_runtime_dependencies(client, monkeypatch):
    from PIL import Image, ImageDraw, ImageFont
    monkeypatch.setattr(client.app.state.ingestion.settings, 'max_upload_bytes', 10 * 1024 * 1024)
    image = Image.new('RGB', (900, 110), 'white')
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 32)
    ImageDraw.Draw(image).text((15, 25), 'Pump P-205B bearing failure', font=font, fill='black')
    stream = BytesIO()
    image.save(stream, format='PNG')
    response = client.post('/api/documents/upload', files={'file': ('ocr.png', stream.getvalue(), 'image/png')})
    assert response.status_code == 200, response.text
    assert 'bearing' in ' '.join(chunk['content'] for chunk in response.json()['chunks']).lower()
