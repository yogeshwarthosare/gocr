import streamlit as st
import os, io
from io import StringIO
from google.cloud import vision
from google.cloud import vision_v1
from google.cloud.vision_v1 import types
from google.cloud import storage
from google.protobuf import json_format
import json
import regex as re
import numpy as np
import pandas as pd
import PyPDF2
#import pybase64
import warnings
warnings.filterwarnings('ignore')
import time





hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>

"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)




st.title("EVERSANA - Optical Character Recognition")
key_error = None

try:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'ocrr-365216-00ff8dd39f68.json'
    client = vision.ImageAnnotatorClient()
except:
    key_error = st.error('Check either your key is expired or some issue with ImageAnnotatorClient()')






if key_error is None:
    document = st.radio('Choose the document type:',
            ['PDF', 'SCANNED IMAGE', 'SCANNED HANDWRITTEN IMAGE'], horizontal=True)


    if document == 'PDF':
        doc = st.file_uploader('Please Upload PDF file', type = ['pdf'])
        global full_text, error
        error = None   
        full_text = ''
        if doc is not None:
            st.write('You have successfully uploaded', doc.name)

            # '''
            # OCR for pdf using google vision
            # '''
            batch_size = 2
            mime_type = 'application/pdf'
            feature = vision_v1.types.Feature(type_ = vision_v1.types.Feature.Type.DOCUMENT_TEXT_DETECTION)
            
            storage_client = storage.Client()
            buckets = list(storage_client.list_buckets())
            bucket = storage_client.get_bucket("ocr_pdf_bucket") # your bucket name
            # ocr_pdf_bucket
            blob = bucket.blob(doc.name)

            # if doc is not None:
            rdoc = doc.read()
            # st.write(type(rdoc))

        
            blob.upload_from_string(rdoc)
            
            gcs_source_uri = 'gs://ocr_pdf_bucket/'+ doc.name # Please give pdf file path
            gcs_source = vision_v1.types.GcsSource(uri = gcs_source_uri)
            input_config = vision_v1.types.InputConfig(gcs_source = gcs_source, mime_type = mime_type)
            
            gcs_destination_uri = 'gs://ocr_pdf_bucket/' + blob.name.split('.')[0] + '/' # Please give pdf file path
            gcs_destination = vision_v1.types.GcsDestination(uri = gcs_destination_uri)
            output_config = vision_v1.types.OutputConfig(gcs_destination = gcs_destination, batch_size = batch_size)
            
            async_request = vision_v1.types.AsyncAnnotateFileRequest(
                features = [feature], input_config = input_config, output_config = output_config)
            
            try:
                operation = client.async_batch_annotate_files(requests = [async_request])
                operation.result(timeout = 360)

            except:
                error = st.warning('Your Pdf file has some error please choose some different pdf file')

            storage_client = storage.Client()
            match = re.match(r'gs://([^/%]+)/(.+)', gcs_destination_uri)
            bucket_name = match.group(1)
            prefix = match.group(2)
            bucket = storage_client.get_bucket(bucket_name)
            
            # List object with the given prefix
            blob_list = list(bucket.list_blobs(prefix = prefix))
            
            
            '''
            
            '''
            for i in range(len(blob_list)):
                if len(blob_list[i].name.split('/')) == 1:
                    continue

                elif blob_list[i].name.split('/')[1][7:9].isnumeric():
                    continue

                else:
                    if blob_list[i].name.split('/')[1][12:14].isnumeric():
                        temp = blob_list[i].name.split('/')[1][:7] + '0' + blob_list[i].name.split('/')[1][7] +  blob_list[i].name.split('/')[1][8:]
                        blob_list[i].name = temp
                        # st.write(blob_list[i].name)
                    else:
                        temp = blob_list[i].name.split('/')[1][:7] + '0' + blob_list[i].name.split('/')[1][7:12] + '0' + blob_list[i].name.split('/')[1][12:]
                        blob_list[i].name = temp
                        # st.write(blob_list[i].name)


            '''
            
            '''    

            if error is None:
                annotation = ''
                st.write('Full text:\n')
                for a in range(1, len(blob_list)+1):
                    for i in range(len(blob_list)):
                        if blob_list[i].name.startswith('output'):
                            output = blob_list[i]
                            json_string = output.download_as_string()
                            response = json.loads(json_string)
                            for j in range(len(response)-1):
                                first_page_response = response['responses'][j]
                                annotation = first_page_response['fullTextAnnotation']
                                st.write(annotation['text'])
                                a = a+1
                                full_text = full_text + ' ' + annotation['text']
                        else:
                            continue
                        
                        
                for i in range(len(blob_list)):
                    if blob_list[i].name.startswith('output'):
                        continue
                    else:
                        output = blob_list[i]
                        json_string = output.download_as_string()
                        response = json.loads(json_string)
                        for j in range(len(response)-1):
                            first_page_response = response['responses'][j]
                            annotation = first_page_response['fullTextAnnotation']
                            # st.write('Full text:\n')
                            st.write(annotation['text'])
                            a = a+1
                            full_text = full_text + '' + annotation['text']

                if full_text is not None:
                    edit_text = st.radio('Do you want to edit the text',['Yes', 'No'], index= 1, horizontal= True)
                    if edit_text == 'No':
                        pass
                    else:
                        full_text = st.text_area('Please make the changes', value= full_text, height= 500)
                    st.download_button('Download',full_text)
                else:
                    pass
            else:
                pass







    if document == 'SCANNED IMAGE':
        doc = st.file_uploader('Please Upload PDF file', type = ['png', 'jpg'])
        global full_text1
        full_text1 = ''
        if doc is not None:
            st.image(doc)
            # '''
            # Description: OCR for images using google vision
            # INPUT: 
            #     1. file_name: png/jpg file name with extension (.png/.jpg)
            #     2. folder_path: path to the folder where the image is store in the device
            # OUTPUT: Text in the image
            # '''
            content = doc.read()
                
            image = vision_v1.types.Image(content = content)
            
            response = client.text_detection(image = image)
            
            texts = response.text_annotations
            
            df = pd.DataFrame(columns = ['locale', 'description'])
            
            for text in texts:
                df = df.append(
                    dict(
                        locale = text.locale,
                        description = text.description
                    ),
                    ignore_index = True
                )
            
            if len(df['description']) > 0 :
                st.write(df['description'][0])    
                full_text1 = full_text1 + '' +df['description'][0]

                if full_text1 is not None:
                    edit_text = st.radio('Do you want to edit the text',['Yes', 'No'], index= 1, horizontal= True)
                    if edit_text == 'No':
                        pass
                    else:
                        full_text1 = st.text_area('Please make the changes', value= full_text1, height= 500)
                    st.download_button('Download',full_text1)
                else:
                    pass
            else:
                st.warning('No text is detected from the image. Please choose another file!')










    if document == 'SCANNED HANDWRITTEN IMAGE':
        doc = st.file_uploader('Please Upload PDF file', type = ['png', 'jpg'])
        global full_text2
        full_text2 = ''
        if doc is not None:
            st.image(doc)
            # '''
            # OCR for handwriting using google vision
            # '''
            
            content = doc.read()
                # st.write(type(content))
            image = vision_v1.types.Image(content = content)
            # st.write(type(content))
            response = client.document_text_detection(image = image)
            
            docText = response.full_text_annotation.text
            st.write(docText)
            full_text2 = full_text2 + '' + docText

            if len(full_text2) > 0:
                edit_text = st.radio('Do you want to edit the text',['Yes', 'No'], index= 1, horizontal= True)
                if edit_text == 'No':
                    pass
                else:
                    full_text2 = st.text_area('Please make the changes', value= full_text2, height= 500)
                st.download_button('Download',full_text2)
            else:
                st.warning('The attachment have no text, Please choose other file!')
