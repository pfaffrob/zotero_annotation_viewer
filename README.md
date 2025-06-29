# Zotero Annotation Viewer

A simple Streamlit-based tool to browse and visualize your Zotero annotations.

## 🛠️ Setup Instructions

Follow these steps to get started:

### 1. Download this repository
Clone or download the ZIP file of this repository to your local machine.

```bash
cd path to your desired directory #(e.g. ~/Desktop)
git clone https://github.com/pfaffrob/zotero-annotation-viewer.git #this creates a folder called zotero-annotation-viewer
```

### 2. Install Zotero  
Download and install Zotero from:  
https://www.zotero.org/download/

### 3. Install the Better BibTeX plugin  
Download and install Better BibTeX plugin for Zotero. More information can be found here:  
https://retorque.re/zotero-better-bibtex/

### 4. Install Anaconda or Miniconda (if not already installed)
Download from:  
https://docs.conda.io/en/latest/miniconda.html

### 5. Create a conda environment (or install packages in an existing environment)

```bash
conda create -n zotero_viewer python=3.11
```

### 6. Activate the environment

```bash
conda activate zotero_viewer
```

### 7. Install dependencies

```bash
conda install -c conda-forge streamlit=1.45.1 pandas=2.2.2
pip install streamlit-autorefresh==1.0.1
```

### 8. Run the Streamlit app
Make sure that you use exactly the same collection name as specified within Zotero. 
Note that the collection name is case-sensitive and cannot contain spaces.

```bash
COLLECTION_NAME=your_collection_name streamlit run annotation_viewer.py
```

