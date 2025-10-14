import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session, joinedload

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from .. import models
from ..database import get_db
from .autenticacao import get_current_user, log_audit_action

router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/pdf", summary="Gera um relatório consolidado em PDF")
def get_relatorio_pdf(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user),
    plano_interno: Optional[str] = Query(None), 
    nd: Optional[str] = Query(None),
    secao_responsavel_id: Optional[int] = Query(None), 
    status: Optional[str] = Query(None),
    incluir_detalhes: bool = Query(False, description="Incluir detalhes de empenhos e recolhimentos no relatório")
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    styles['h1'].alignment = 1 # Center alignment
    styles['h2'].alignment = 1
    
    elements = []
    
    # Cabeçalho
    header_text = "MINISTÉRIO DA DEFESA<br/>EXÉRCITO BRASILEIRO<br/>2º CENTRO DE GEOINFORMAÇÃO"
    elements.append(Paragraph(header_text, styles['h2']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Título
    titulo = "RELATÓRIO GERAL DE NOTAS DE CRÉDITO"
    elements.append(Paragraph(titulo, styles['h1']))
    elements.append(Paragraph(f"Gerado por: {current_user.username} em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Query principal
    query = db.query(models.NotaCredito).options(
        joinedload(models.NotaCredito.secao_responsavel),
        joinedload(models.NotaCredito.empenhos),
        joinedload(models.NotaCredito.recolhimentos)
    ).order_by(models.NotaCredito.plano_interno)
    
    # Filtros
    if plano_interno: query = query.filter(models.NotaCredito.plano_interno.ilike(f"%{plano_interno}%"))
    if nd: query = query.filter(models.NotaCredito.nd.ilike(f"%{nd}%"))
    if secao_responsavel_id: query = query.filter(models.NotaCredito.secao_responsavel_id == secao_responsavel_id)
    if status: query = query.filter(models.NotaCredito.status.ilike(f"%{status}%"))
    
    ncs = query.all()
    
    if not ncs:
        elements.append(Paragraph("Nenhuma Nota de Crédito encontrada para os filtros selecionados.", styles['Normal']))
    else:
        for nc in ncs:
            nc_data = [[
                Paragraph(f"<b>NC:</b> {nc.numero_nc}", styles['Normal']),
                Paragraph(f"<b>PI:</b> {nc.plano_interno}", styles['Normal']),
                Paragraph(f"<b>ND:</b> {nc.nd}", styles['Normal']),
                Paragraph(f"<b>Seção:</b> {nc.secao_responsavel.nome}", styles['Normal']),
            ], [
                Paragraph(f"<b>Valor:</b> R$ {nc.valor:,.2f}", styles['Normal']),
                Paragraph(f"<b>Saldo:</b> R$ {nc.saldo_disponivel:,.2f}", styles['Normal']),
                Paragraph(f"<b>Status:</b> {nc.status}", styles['Normal']),
                Paragraph(f"<b>Prazo:</b> {nc.prazo_empenho.strftime('%d/%m/%Y')}", styles['Normal']),
            ]]
            
            tbl = Table(nc_data, colWidths=[2.7*inch, 2.7*inch, 2.7*inch, 2.7*inch])
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#E6E6E6")),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BOX', (0,0), (-1,-1), 2, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(tbl)
            
            if incluir_detalhes:
                if nc.empenhos:
                    elements.append(Spacer(1, 0.1*inch))
                    empenhos_data = [["<b>Empenhos da NC</b>", "", "", ""], ["Nº da NE", "Valor", "Data", "Observação"]]
                    for e in nc.empenhos:
                        empenhos_data.append([e.numero_ne, f"R$ {e.valor:,.2f}", e.data_empenho.strftime('%d/%m/%Y'), e.observacao or ''])
                    
                    empenhos_tbl = Table(empenhos_data, colWidths=[2.7*inch, 2.7*inch, 2.7*inch, 2.7*inch])
                    empenhos_tbl.setStyle(TableStyle([
                        ('SPAN', (0,0), (-1,0)), ('ALIGN', (0,0), (-1,0), 'CENTER'),
                        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
                        ('GRID', (0,1), (-1,-1), 1, colors.grey),
                    ]))
                    elements.append(empenhos_tbl)

                if nc.recolhimentos:
                    elements.append(Spacer(1, 0.1*inch))
                    recolhimentos_data = [["<b>Recolhimentos da NC</b>", "", ""], ["Valor", "Data", "Observação"]]
                    for r in nc.recolhimentos:
                        recolhimentos_data.append([f"R$ {r.valor:,.2f}", r.data.strftime('%d/%m/%Y'), r.observacao or ''])

                    recolhimentos_tbl = Table(recolhimentos_data, colWidths=[3.6*inch, 3.6*inch, 3.6*inch])
                    recolhimentos_tbl.setStyle(TableStyle([
                        ('SPAN', (0,0), (-1,0)), ('ALIGN', (0,0), (-1,0), 'CENTER'),
                        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
                        ('GRID', (0,1), (-1,-1), 1, colors.grey),
                    ]))
                    elements.append(recolhimentos_tbl)
            
            elements.append(Spacer(1, 0.2*inch))

    doc.build(elements)
    buffer.seek(0)
    
    headers = {'Content-Disposition': 'inline; filename="relatorio_salc.pdf"'}
    log_audit_action(db, current_user.username, "REPORT_GENERATED", f"Filtros: PI={plano_interno}, ND={nd}, Seção={secao_responsavel_id}, Status={status}")
    db.commit()
    
    return Response(content=buffer.getvalue(), media_type='application/pdf', headers=headers)