import streamlit as st
import yaml
import os
import tkinter as tk
from tkinter import filedialog
from scripts.report_engine import ReportEngine

st.set_page_config(page_title="Gerador de Relatórios Fotográficos", layout="wide")

# CSS para ajuste fino de layout
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 2rem; }
        header { visibility: hidden; height: 0px; }
    </style>
    """, unsafe_allow_html=True)

def select_folder(label, key_suffix, default_path):
    st.write(f"**{label}**")
    if st.button("Selecionar Pasta", icon=":material/folder:", key=f"btn_folder_{key_suffix}", use_container_width=True):
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        selected_path = filedialog.askdirectory(initialdir=os.getcwd()); root.destroy()
        if selected_path:
            st.session_state[f"path_{key_suffix}"] = selected_path
            st.rerun()
    current_path = st.session_state.get(f"path_{key_suffix}", default_path)
    st.caption(f":material/file_map: {current_path}")
    return current_path

def select_file(label, key_suffix, default_path):
    st.write(f"**{label}**")
    if st.button("Abrir Arquivo Excel", icon=":material/file_open:", key=f"btn_file_{key_suffix}", use_container_width=True):
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        selected_file = filedialog.askopenfilename(initialdir=os.getcwd(), filetypes=[("Excel files", "*.xlsx")]); root.destroy()
        if selected_file:
            st.session_state[f"file_{key_suffix}"] = selected_file
            st.rerun()
    current_path = st.session_state.get(f"file_{key_suffix}", default_path)
    st.caption(f":material/file_map: {current_path}")
    return current_path

def load_config_to_session():
    if 'sections' not in st.session_state:
        config_path = "config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            st.session_state.path_template = data['paths'].get('template', "")
            st.session_state.path_images = data['paths'].get('base_images', "")
            st.session_state.output_filename = os.path.basename(data['paths'].get('output', "relatorio_final.xlsx"))
            
            loaded_sections = []
            for s in data.get('sections', []):
                sec = {"id": s['id'], "label": s['label'], "max_photos": s['max_photos'], "fix_width": s['fix_width']}
                if 'num_pavimentos' in s:
                    sec['num_pavimentos'] = ", ".join(map(str, s['num_pavimentos']))
                loaded_sections.append(sec)
            st.session_state.sections = loaded_sections
        else:
            st.session_state.sections = []

load_config_to_session()

with st.sidebar:
    st.header(":material/settings: Configurações")
    template_path = select_file("Template Excel", "template", st.session_state.get('path_template', ""))
    base_img_path = select_folder("Pasta Raiz das Imagens", "images", st.session_state.get('path_images', ""))
    st.divider()
    output_filename = st.text_input("Nome do Arquivo de Saída", st.session_state.get('output_filename', "relatorio_final.xlsx"))
    output_path = os.path.join(os.path.dirname(template_path), output_filename)
    sort_method = st.selectbox("Ordenar fotos por", ["date", "name"], index=0)

st.title("Relatório Fotográfico de Obras")
st.subheader(":material/list: Definição de Seções")

for idx, section in enumerate(st.session_state.sections):
    with st.expander(f"Seção: {section['label']}", expanded=True):
        col1, col2, col3, col4, col5 = st.columns([2.5, 3.5, 1.2, 1.2, 0.8])
        with col1:
            st.session_state.sections[idx]['id'] = st.text_input("Pasta", section['id'], key=f"id_{idx}")
        with col2:
            st.session_state.sections[idx]['label'] = st.text_input("Título Excel", section['label'], key=f"lbl_{idx}")
        with col3:
            st.session_state.sections[idx]['max_photos'] = st.number_input("Fotos", 1, 500, int(section['max_photos']), key=f"max_{idx}")
        with col4:
            st.write('<div style="margin-top: 5px;"></div>', unsafe_allow_html=True)
            st.session_state.sections[idx]['fix_width'] = st.checkbox("Fixar Largura?", section['fix_width'], key=f"fix_{idx}")
        with col5:
            st.write('<div style="margin-top: 25px;"></div>', unsafe_allow_html=True)
            if st.button(":material/delete:", key=f"del_{idx}"):
                st.session_state.sections.pop(idx)
                st.rerun()
        if section['id'] == 'pavimentos' or 'num_pavimentos' in section:
            st.session_state.sections[idx]['num_pavimentos'] = st.text_area("Distribuição de Pavimentos", section.get('num_pavimentos', ""), key=f"pav_{idx}")

if st.button("Adicionar Nova Seção", icon=":material/add:", use_container_width=True):
    st.session_state.sections.append({"id": "nova_secao", "label": "Nova Seção", "max_photos": 1, "fix_width": False})
    st.rerun()

if st.button("GERAR RELATÓRIO", icon=":material/bolt:", type="primary", use_container_width=True):
    try:
        config_data = {
            "paths": {"template": template_path, "output": output_path, "base_images": base_img_path},
            "project_metadata": {"project_name": "Relatório", "target_sheet": "Relatório fotográfico", "default_font": "Arial", "default_font_size": 18},
            "layout_settings": {"photo_columns": ["B", "D", "F"], "image_span": 10, "row_spacing": 2, "default_min_row_height": 23.25, "fixed_width_px": 390, "sort_method": sort_method},
            "sections": []
        }
        for s in st.session_state.sections:
            sec_dict = {"id": s["id"], "label": s["label"], "max_photos": s["max_photos"], "fix_width": s["fix_width"]}
            if "num_pavimentos" in s and s["num_pavimentos"]:
                sec_dict["num_pavimentos"] = [int(x.strip()) for x in str(s["num_pavimentos"]).split(",") if x.strip()]
            config_data["sections"].append(sec_dict)

        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)

        with st.status(":material/build: Construindo Relatório...", expanded=True) as status:
            def update_progress(percent, msg):
                progress_bar.progress(percent)
                status_text.markdown(f"**Status:** {msg}")

            progress_bar = st.progress(0)
            status_text = st.empty()
            engine = ReportEngine("config.yaml")
            engine.load_excel_template()
            photos_map = {s['id']: os.path.join(base_img_path, s['id']) for s in config_data['sections']}
            engine.insert_images_in_report(photos_map, callback=update_progress)
            engine.save_and_close()
            status.update(label="Relatório Concluído!", state="complete", expanded=False)
        st.success(f"Arquivo salvo: {output_path}")
    except Exception as e:
        st.error(f"Erro: {str(e)}")