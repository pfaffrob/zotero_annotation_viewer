import os
import sys
import streamlit as st
import pandas as pd
import json
from streamlit_autorefresh import st_autorefresh
import base64
import json
import sqlite3
import shutil
import os
import glob
import time
import fitz
from config import *

import sys

COLLECTION_NAME = os.getenv("COLLECTION_NAME")
if not COLLECTION_NAME:
    sys.exit(
        "\n❌ Error: The environment variable COLLECTION_NAME is required.\n"
        "Please run the app like this:\n\n"
        "COLLECTION_NAME=my_collection streamlit run annotation_viewer.py\n"
    )

def copy_zotero_db():
    shutil.copy2(ZOTERO_DB_PATH, DB_COPY_PATH)

def copy_bibtex_db():
    shutil.copy2(BTEX_DB_PATH, BTEX_DB_COPY_PATH)


def get_item_keys(collection_name):
    copy_zotero_db()
    conn = sqlite3.connect(DB_COPY_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT items.key
        FROM items
        JOIN collectionItems ON items.itemID = collectionItems.itemID
        JOIN collections ON collectionItems.collectionID = collections.collectionID
        WHERE collections.collectionName = ?;
    """, (collection_name,))
    item_keys = [row[0] for row in cursor.fetchall()]
    conn.close()
    return item_keys

def get_annotations(item_key):
    copy_zotero_db()
    conn = sqlite3.connect(DB_COPY_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT itemAnnotations.itemID, annItems.key AS annotation_key,
               itemAnnotations.parentItemID, itemAnnotations.type,
               itemAnnotations.authorName, itemAnnotations.text,
               itemAnnotations.comment, itemAnnotations.color,
               itemAnnotations.pageLabel, itemAnnotations.sortIndex,
               itemAnnotations.position, itemAnnotations.isExternal,
               attItems.key AS attachment_key, attItems.itemID AS attachmentItemID, att.path
        FROM itemAnnotations
        JOIN items AS annItems ON itemAnnotations.itemID = annItems.itemID
        JOIN itemAttachments AS att ON itemAnnotations.parentItemID = att.itemID
        JOIN items AS attItems ON att.itemID = attItems.itemID
        JOIN items AS parentItems ON att.parentItemID = parentItems.itemID
        WHERE parentItems.key = ?;
    """, (item_key,))
    
    annotations = []
    for row in cursor.fetchall():
        annotation_id = row[0]
        
        cursor.execute("""
            SELECT tags.name
            FROM itemTags
            JOIN tags ON itemTags.tagID = tags.tagID
            WHERE itemTags.itemID = ?;
        """, (annotation_id,))
        
        tags = [tag_row[0] for tag_row in cursor.fetchall()]
        
        annotations.append({
            "annotation_id": row[0],
            "annotation_key": row[1],
            "parent_item_id": row[2],
            "type": row[3],
            "author_name": row[4],
            "text": row[5],
            "comment": row[6],
            "color": row[7],
            "page": row[8],
            "sort_index": row[9],
            "position": row[10],
            "is_external": row[11],
            "attachment_key": row[12],
            "attachment_item_id": row[13],
            "attachment_path": row[14],
            "parent_item_key": item_key,
            "tags": tags
        })
    
    conn.close()
    return annotations

def get_bibtex_citekey(item_key):
    copy_bibtex_db()
    conn = sqlite3.connect(BTEX_DB_COPY_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT citationKey
        FROM citationkey
        WHERE itemKey = ?;
    """, (item_key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else item_key

def get_metadata(item_key):
    copy_zotero_db()
    conn = sqlite3.connect(DB_COPY_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.key, date_val.value AS year, 
               group_concat(c.lastName || ', ' || c.firstName, ', ') AS authors,
               title_val.value AS title, url_val.value AS url, abstract_val.value AS abstract
        FROM items i
        LEFT JOIN itemData d_date ON i.itemID = d_date.itemID AND d_date.fieldID = 6
        LEFT JOIN itemDataValues date_val ON d_date.valueID = date_val.valueID
        LEFT JOIN itemCreators ic ON i.itemID = ic.itemID
        LEFT JOIN creators c ON ic.creatorID = c.creatorID
        LEFT JOIN itemData d_title ON i.itemID = d_title.itemID AND d_title.fieldID = 1
        LEFT JOIN itemDataValues title_val ON d_title.valueID = title_val.valueID
        LEFT JOIN itemData d_url ON i.itemID = d_url.itemID AND d_url.fieldID = 13
        LEFT JOIN itemDataValues url_val ON d_url.valueID = url_val.valueID
        LEFT JOIN itemData d_abstract ON i.itemID = d_abstract.itemID AND d_abstract.fieldID = 2
        LEFT JOIN itemDataValues abstract_val ON d_abstract.valueID = abstract_val.valueID
        WHERE i.key = ?
        GROUP BY i.key;
    """, (item_key,))
    row = cursor.fetchone()
    conn.close()
    year = row[1][:4] if row and row[1] else "n.d."
    return {
        "citekey": row[0] if row else item_key,
        "year": year,
        "authors": row[2] if row else "",
        "title": row[3] if row else "",
        "url": row[4] if row else "",
        "abstract": row[5] if row else "",
    }

def export_image_from_pdf(pdf_path, annotation, output_path, dpi=300):
    import fitz
    doc = fitz.open(pdf_path)
    position = json.loads(annotation["position"])
    page_index = position["pageIndex"]
    rects = position["rects"]
    page = doc.load_page(page_index)
    page_height = page.rect.height

    for i, rect in enumerate(rects):
        x0, y0, x1, y1 = rect
        fitz_rect = fitz.Rect(x0, page_height - y1, x1, page_height - y0)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, clip=fitz_rect)
        pix.save(output_path)
        return output_path


def try_copy(src_path, dest_path, attempts=4, delay=0.25):
    src = Path(src_path).expanduser()
    dest = Path(dest_path).expanduser()
    for _ in range(attempts):
        try:
            shutil.copy2(src, dest)
            return
        except Exception:
            time.sleep(delay)

import time

def extract_zotero_data():
    data = []
    for attempt in range(4):
        try:
            item_keys = get_item_keys(COLLECTION_NAME)
            for item_key in item_keys:
                annotations = get_annotations(item_key)
                metadata = get_metadata(item_key)
                bibtex_key = get_bibtex_citekey(item_key)

                for ann in annotations:
                    annotation_text = ann["text"]
                    annotation_image_path = ""

                    if not annotation_text and ann["type"] == 3:
                        attachment_path = os.path.join(ZOTERO_STORAGE_PATH, ann["attachment_key"])
                        pdf_files = glob.glob(os.path.join(attachment_path, "*.pdf"))
                        if pdf_files:
                            annotation_image_path = f"{IMAGES_OUTPUT_DIR}/{bibtex_key}/image-{ann['page']}-{ann['annotation_key']}.png"
                            os.makedirs(os.path.dirname(annotation_image_path), exist_ok=True)
                            export_image_from_pdf(pdf_files[0], ann, annotation_image_path)

                    data.append({
                        "year": metadata["year"],
                        "citekey": bibtex_key,
                        "link": metadata["url"],
                        "annotation_text": annotation_text,
                        "annotation_image": annotation_image_path,
                        "comment": ann["comment"],
                        "color": ann["color"],
                        "zotero": f'zotero://open-pdf/library/items/{ann["attachment_key"]}?page={ann["page"]}&annotation={ann["annotation_key"]}',
                        "tags": ", ".join(ann["tags"])
                    })
                    #print(data)
            #return data

            with open("zotero_data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            break  # success, exit retry loop

        except Exception as e:
            time.sleep(0.2)
            print(f"Attempt {attempt + 1} failed: {e}")
            #print(e)
            # if attempt == 3:
            #     if len(data) > 0:
            #         with open("zotero_data.json", "w", encoding="utf-8") as f:
            #             json.dump(data, f, indent=2)





def load_data():
    with open("zotero_data.json", "r", encoding="utf-8") as f:
        df = pd.DataFrame(json.load(f))

    def convert_image_to_base64(image_path):
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode()
                return f"data:image/png;base64,{encoded}"
        return ""

    df["annotation_image"] = df["annotation_image"].apply(convert_image_to_base64)
    return df


def main():


    
    st.set_page_config(layout="wide")
    st.title("Zotero Annotations Viewer")

        # Sidebar controls
    enable_autorefresh = st.sidebar.checkbox("Auto-Refresh", value=True)
    if enable_autorefresh:
        st_autorefresh(interval=30000, key="datarefresh")

    if st.sidebar.button("🔄 Manual Refresh"):
        st.rerun()

    extract_zotero_data()
        

    df = load_data()
    
    # Convert 'year' to integer type for filtering
    df["year"] = df["year"].astype(int)
    
    # Map hex codes to human-readable color names
    ZOTERO_COLOR_MAP = {
        "#ffd400": "🟡 Information",
        "#ff6666": "🔴 Contradiction",
        "#5fb236": "🟢 Overlap/Reasoning",
        "#a28ae5": "🟣 limitation",
        "#f19837": "🟠 Question/Unclarity",
        "#aaaaaa": "⚪ Technical Term",
        "#2ea8e5": "🔵 undefined",
        "#e56eee": "🩷 undefined",
    }


    # Add a new column with readable color names
    df["color_name"] = df["color"].map(ZOTERO_COLOR_MAP)
    
    # Sidebar filter
    all_tags = sorted(set(tag for tags in df["tags"] for tag in tags.split(", ") if tag))
    selected_tags = st.sidebar.multiselect("Filter by Tag", all_tags)

    # Filter data
    if selected_tags:
        df = df[df["tags"].apply(lambda tag_str: any(tag in tag_str.split(", ") for tag in selected_tags))]
    
    # Year slider filter
    min_year, max_year = df["year"].min(), df["year"].max()
    if max_year - min_year > 0:
        selected_year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))
        df = df[df["year"].between(*selected_year_range)]

    # Sidebar color filter
    all_colors = sorted(df["color_name"].dropna().unique())
    selected_colors = st.sidebar.multiselect("Filter by Color", all_colors)
    if selected_colors:
        df = df[df["color_name"].isin(selected_colors)]

        
    # Citekey filter
    all_citekeys = sorted(df["citekey"].dropna().unique())
    selected_papers = st.sidebar.multiselect("Filter by Paper", all_citekeys)
    if selected_papers:
        df = df[df["citekey"].isin(selected_papers)]
        
    


    def style_row_by_color(row):
        return [f"color: {row['color']}" if col == "annotation_text" else "" for col in row.index]


    # Reorder the DataFrame columns
    df = df[["year", "citekey", "annotation_text", "annotation_image", "comment", "zotero", "link", "tags", "color"]]
    
    df = df.style.apply(style_row_by_color, axis=1)
    # Display DataFrame with reordered columns
    st.dataframe(
        df,
        column_config={
            "annotation_image": st.column_config.ImageColumn("Image", width="small"),
            "link": st.column_config.LinkColumn(width="small", display_text="web"),
            "zotero": st.column_config.LinkColumn(width="small", display_text="pdf"),
            "citekey": st.column_config.TextColumn("Citekey", width="small"),
            "year": st.column_config.TextColumn("Year"),
            "annotation_text": st.column_config.TextColumn("Annotation Text", width="wide"),
            "tags": st.column_config.TextColumn("Tags", width="medium"),
            "comment": st.column_config.TextColumn("Comment", width="medium"),
            "color": None,
            "color_name": None
        },
        hide_index=True
    )


if __name__ == "__main__":
    import sys

    COLLECTION_NAME = os.getenv("COLLECTION_NAME")
    if not COLLECTION_NAME:
        sys.exit(
            "\n❌ Error: The environment variable COLLECTION_NAME is required.\n"
            "Please run the app like this:\n\n"
            "COLLECTION_NAME=my_collection streamlit run annotation_viewer.py\n"
        )
    extract_zotero_data()
    main()
