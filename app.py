from flask import Flask,request,render_template,jsonify
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import os
import seaborn as sns
import matplotlib.pyplot as plt
import json

app=Flask(__name__)
model = pickle.load(open('kmeans_model.pkl','rb'))

def load_and_clean_data(file_path):
    #load data
    retail = pd.read_csv('OnlineRetail.csv', sep="," ,encoding = 'ISO-8859-1',header=0)
    retail['CustomerID'] = retail['CustomerID'].astype(str)
    retail['Amount'] = retail ['Quantity']*retail['UnitPrice'] 
    rfm_m = retail.groupby('CustomerID')['Amount'].sum().reset_index()
    
    rfm_f = retail.groupby('CustomerID')['InvoiceNo'].count().reset_index()
    rfm_f.columns = ['CustomerID', 'Frequency']
    retail['InvoiceDate'] = pd.to_datetime(retail['InvoiceDate'],format='%m/%d/%Y %H:%M')
    max_date = max(retail['InvoiceDate'])
    retail['Diff'] = max_date - retail['InvoiceDate']

    rfm_p = retail.groupby('CustomerID')['Diff'].min().reset_index()
    rfm_p['Diff'] = rfm_p['Diff'].dt.days
    rfm = pd.merge(rfm_m,rfm_f,on='CustomerID', how='inner')
    rfm = pd.merge(rfm,rfm_p,on='CustomerID', how='inner')
    rfm.columns = ['CustomerID','Amount' ,'Frequency', 'Recency']

    Q1=rfm.Recency.quantile(0.05)
    Q3=rfm.Recency.quantile(0.95)
    IQR=Q3-Q1
    rfm=rfm[(rfm.Amount >=Q1 -1.5*IQR) & (rfm.Amount <=Q3 + 1.5*IQR)]
    rfm=rfm[(rfm.Recency >=Q1 -1.5*IQR) & (rfm.Recency <=Q3 + 1.5*IQR)]
    rfm=rfm[(rfm.Frequency >=Q1 -1.5*IQR) & (rfm.Frequency <=Q3 + 1.5*IQR)]
    return rfm;

def preprocess_data(file_path):
    rfm = load_and_clean_data(file_path)
    rfm_df = rfm[['Amount', 'Frequency', 'Recency']]
    scaler = StandardScaler()
    rfm_df_scaled = scaler.fit_transform(rfm_df)
    rfm_df_scaled=pd.DataFrame(rfm_df_scaled)
    rfm_df_scaled.columns = ['Amount', 'Frequency', 'Recency']

    return rfm,rfm_df_scaled;


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict',methods=['POST'])

@app.route('/predict', methods=['POST'])
def predict():
    file = request.files['file']
    file_path = os.path.join(os.getcwd(), file.filename)
    file.save(file_path)
    df = preprocess_data(file_path)[1]
    results_df = model.predict(df)
    results_df = pd.DataFrame(results_df)
    df_with_id = preprocess_data(file_path)[0]
    df_with_id['Cluster'] = results_df

    # Generate the image and save them using matplotlib
    plt.figure(figsize=(10, 6))

    # Plot for Amount
    plt.subplot(1, 3, 1)
    sns.stripplot(x='Cluster', y='Amount', data=df_with_id, hue='Cluster')
    plt.title('Amount')

    # Plot for Frequency
    plt.subplot(1, 3, 2)
    sns.stripplot(x='Cluster', y='Frequency', data=df_with_id, hue='Cluster')
    plt.title('Frequency')

    # Plot for Recency
    plt.subplot(1, 3, 3)
    sns.stripplot(x='Cluster', y='Recency', data=df_with_id, hue='Cluster')
    plt.title('Recency')

    # Save the plot
    img_path = 'static/cluster_plots.png'
    plt.savefig(img_path)
    plt.clf()  # Clear the current figure

    response = {
        'img_path': img_path
    }

    return jsonify(response)

   
if __name__ == '__main__':
    app.run(debug=True)