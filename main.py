import sys
import random
#import pandas as pd
#import numpy as np
sys.path.append('./Code')
from Code.OECT import *

def parse_args():
    parser = argparse.ArgumentParser(description='OFET mobility prediction')
    parser.add_argument('--OECT_file', type=str, default='data/OECT0.csv',help='Path for experimental OECTs data file')
    parser.add_argument('--Units_file', type=str, default='data/Collected_Units.csv',help='Path for Polymer fragments file')
    parser.add_argument('--OECTs_features', type=list, default=['HOMO(eV)','LUMO(eV)'],help='OECTs Features that will be processed')
    parser.add_argument('--OECTs_properties', type=list, default=['uC*','Vth(eV)','u_h','u_e'], help='OECTs properties')
    parser.add_argument('--OFETs_h_model',type=str,default='module/OFET_prediction/Features_12D_hole/',help='Path for OFETs hole mobility predition model')
    parser.add_argument('--OFETs_e_model',type=str,default='module/OFET_prediction/Features_12D_electron/',help='Path for OFETs electron mobility predition model')
    parser.add_argument('--Unimol_Plan_module',type=str,default='module/Unimolsave',help='The path of finetuned Unimol model for planarity prediction')
    parser.add_argument('--OFETs_features',default=list,default=['HOMO(eV)','LUMO(eV)','COS2-0','COS2-1','COS2-2','COS2-3','COS2-4','COS2-5','COS2-6','COS2-7','COS2-8','COS2-9'],help='Features of OFETs mobility prediction model')
    parser.add_argument('--Unimol_HL_module',type=str,default='module/UnimolHLsave_INPUT/',help='The path of finetuned Unimol model for HOMO and LUMO prediction')
    parser.add_argument('--OECTs_features_e',default=list,default==['LUMO(eV)','HOMO(eV)', 'Delta_HOMO','Delta_LUMO','ue_pred'],help='Features of N-type OECTs properties prediction model')
    parser.add_argument('--OECTs_features_h',default=list,default==['LUMO(eV)','HOMO(eV)', 'Delta_HOMO','Delta_LUMO','uh_pred'],help='Features of P-type OECTs properties prediction model')
    parser.add_argument('--OECTs_candidate',type=str,default='data/Generate_2units.npy',help='The path of genrated polymers')
    parser.add_argument('--OECTs_features_selection_PT_N',type=str,default='module/uhC_4features-uC/',help='Data storage path generated during the screening of OECTs property prediction features')
    args = parser.parse_args([])
    return args

def main(choice):
    args=parse_args()
    
    OECT_file,Units_file,features,targets,module=args.OECT_file,args.Units_file,args.OECTs_features,args.OECTs_properties,args.Unimol_Plan_module
    OFET_h_m,OFET_e_m=args.OFETs_h_model,args.OFETs_e_model
    OFET_features=args.OFETs_features
    HL_module=args.Unimol_HL_module
    dataset_file=args.OECTs_candidate          
    fea=Get_fea_data(OECT_file,Units_file,features,targets,module,OFET_h_m,OFET_e_m,OFET_features)
    feature_e_name=args.OECTs_features_e
    feature_h_name=args.OECTs_features_h
    
    df0=pd.DataFrame(fea['Smiles'])
    df0.columns=['SMILES']
    df0.to_csv(f'Pol.csv',index=None)
    pred_m=MolPredict(load_model=HL_module)
    
    pred_HL=pred_m.predict(f'Pol.csv')
    os.remove(f"Pol.csv")
    
    fea['HOMO(eV)']=[x[0] for x in pred_HL]
    fea['LUMO(eV)']=[x[1]-0.8 for x in pred_HL]
    
    if choice==1:#特征筛选\
        PT=args.OECTs_features_selection_PT
        #Train_uC_Nfeatures(fea,4,'uC*',PT)
        #Train_uC_Nfeatures(fea,2,'uC*',PT)
        #模型特征提取
        path=PT+'ueC_4features-uC/'
        df=Get_F_Part(path,save_file='ueC_4_features.csv')
        path=PT+'uhC_4features-uC/'
        df2=Get_F_Part(path,save_file='uhC_4_features.csv')
        feat1=pd.DataFrame(index=[0],columns=list(df.columns.values)[:-2])
        feat2=pd.DataFrame(index=[0],columns=list(df2.columns.values)[:-2])
        for col in df.columns.values[:-2]:
            feat1[col][0]=np.sum(df[col][-60:])
            feat2[col][0]=np.sum(df2[col][-60:])
        feature_e=feat1.iloc[0,:].astype(float).nlargest(feat1.shape[1]).index
        feature_h=feat2.iloc[0,:].astype(float).nlargest(feat2.shape[1]).index
        print('The following features are sorted by frequency of occurrence in models with R2 more than 0.4')
        print('n type OECT:',feature_e)
        print('p type OECT:',feature_h)
        return feature_h,feature_e
    
    if choice==2:#module
        #feature_h,feature_e=main(1)
        #feature_h_name=features
        #feature_e_name=[]
        col=list(set(feature_h_name+feature_e_name))#+
        targets=['u_h','u_e']
        features=pd.DataFrame(index=[i for i in range(len(fea['u_h']))],columns=col+targets)
        features['ueC*']=[0 for i in range(features.shape[0])]
        features['uhC*']=[0 for i in range(features.shape[0])]
        for f in col+targets:
            features[f]=fea[f]
        for i in range(features.shape[0]):
            if fea['u_h'][i]!=0 and not np.isnan(fea['u_h'][i]):
                features['uhC*'][i]=fea['uC*'][i]
            if fea['u_e'][i]!=0 and not np.isnan(fea['u_e'][i]):
                features['ueC*'][i]=fea['uC*'][i]
         
        RS=[113,199,325,52,761]
        model_h,model_e=[],[]
        for i in tqdm(range(len(RS))):
            T=['uhC*']
            df_FT=features[feature_h_name+T]
            df_FT=df_FT.drop_duplicates().reset_index().drop(['index'],axis=1)
            x_h_train,y_h_train,x_h_test,y_h_test,N=Data_split(RS[i],0.9,df_FT[feature_h_name].values,df_FT[T].values.reshape(-1),log=True)
            X_train, X_val, y_train, y_val = x_h_train,x_h_test,y_h_train,y_h_test
            final_model_h = XGBRegressor(random_state=42)                
            final_model_h.fit(X_train, y_train)
            val_preds = final_model_h.predict(X_val)
            val_r2 = r2_score(y_val, val_preds)
            model_h.append(final_model_h)
        RS=[9308,6395,9887,3827,9265]
        for i in tqdm(range(len(RS))):      
            T=['ueC*']
            df_FT0=features[feature_e_name+T]
            df_FT=df_FT0.drop_duplicates().reset_index().drop(['index'],axis=1)
            x_e_train,y_e_train,x_e_test,y_e_test,N=Data_split(RS[i],0.9,df_FT[feature_e_name].values,df_FT[T].values.reshape(-1),log=True)
            X_train, X_val, y_train, y_val = x_e_train,x_e_test,y_e_train,y_e_test
            final_model_e = XGBRegressor(random_state=42)
            final_model_e.fit(X_train, y_train)            
            val_preds = final_model_e.predict(X_val)
            val_r2 = r2_score(y_val, val_preds)
            model_e.append(final_model_e)
            
        return model_h,model_e
    
    if choice==3:
        df=Get_dataset_feature(dataset_file,HL_module,module,Units_file,OFET_fea,OFET_h_m,OFET_e_m)
        final_model_h,final_model_e=[],[]
        uhC,ueC=np.zeros(df.shape[0]),np.zeros(df.shape[0])
        mh,me=main(2)
        for i in range(len(mh)):
            uhC+=mh[i].predict(df[feature_h_name].values)/len(mh)
        for i in range(len(me)):    
            ueC+=me[i].predict(df[feature_e_name].values)/len(me)
        dataset=np.load(dataset_file,allow_pickle=True).item()
        h_max=np.argsort(uhC)[-len(uhC):][::-1]
        e_max=np.argsort(ueC)[-len(ueC):][::-1]
        for i in range(10):
            print(f'{i} P type:',dataset['Polymer_smile'][h_max[i]],'uC* value:',uhC[h_max[i]])
            print(f'{i} N type:',dataset['Polymer_smile'][e_max[i]],'uC* Value',ueC[e_max[i]])
        return h_max,e_max,uhC,ueC
    
    if choice==4:
        HL_module='module/UnimolHLsave_INPUT'
        dataset_file='data/Generate_2units.npy'            
        #df=Get_dataset_feature(dataset_file,HL_module,module,Units_file,OFET_fea,OFET_h_m,OFET_e_m)
        col1= ['LUMO(eV)','HOMO(eV)', 'Delta_HOMO','Delta_LUMO','ue_pred']
        col2= ['LUMO(eV)','HOMO(eV)', 'Delta_HOMO','Delta_LUMO','uh_pred']
        targets=['u_h','u_e','Vth(eV)']
        col=list(set(col1+col2))
        features=pd.DataFrame(index=[i for i in range(len(fea['u_h']))],columns=col+targets+['Vth_e','Vth_h'])
        for f in col+targets:
            features[f]=fea[f]
            
        for i in range(features.shape[0]):
            if fea['u_h'][i]!=0 and not np.isnan(fea['u_h'][i]) and not np.isnan(fea['Vth(eV)'][i]):
                features['Vth_h'][i]=fea['Vth(eV)'][i]
            if fea['u_e'][i]!=0 and not np.isnan(fea['u_e'][i]) and not np.isnan(fea['Vth(eV)'][i]):
                features['Vth_e'][i]=fea['Vth(eV)'][i]

        RS=[9589,638,5310,4713,7510]
        model1=[]
        for i in tqdm(range(len(RS))):      
            df_FT0=features[col1+['Vth_e']]
            df_FT=df_FT0.drop_duplicates().reset_index().drop(['index'],axis=1)
            x_train,y_train,x_test,y_test,N=Data_split(RS[i],0.9,df_FT[col1].values,df_FT['Vth_e'].values.reshape(-1),log=False)
            X_train, X_val, y_train, y_val = x_train,x_test,y_train,y_test
            final_model = XGBRegressor(random_state=42)
            final_model.fit(X_train, y_train)            
            val_preds = final_model.predict(X_val+X_train)
            val_r2 = r2_score(y_val+y_train, val_preds)
            model1.append(final_model)
            
        RS=[5326,6937,6170,6102,7638]
        model2=[]
        for i in tqdm(range(len(RS))):      
            df_FT0=features[col2+['Vth_h']]
            df_FT=df_FT0.drop_duplicates().reset_index().drop(['index'],axis=1)
            x_train,y_train,x_test,y_test,N=Data_split(RS[i],0.9,df_FT[col2].values,df_FT['Vth_h'].values.reshape(-1),log=False)
            X_train, X_val, y_train, y_val = x_train,x_test,y_train,y_test
            final_model = XGBRegressor(random_state=42)
            final_model.fit(X_train, y_train)            
            val_preds = final_model.predict(X_val+X_train)
            val_r2 = r2_score(y_val+y_train, val_preds)
            model2.append(final_model)
        Vth_e=np.zeros(df.shape[0])
        Vth_h=np.zeros(df.shape[0])
        for i in range(len(model1)):    
            Vth_e+=model1[i].predict(df[col1].values)/len(model)
        for i in range(len(model2)):    
            Vth_h+=model2[i].predict(df[col2].values)/len(model)
        return Vth_h,Vth_e,model2,model1

if __name__ == "__main__":
    features_h,features_e,uhc,uec=main(3,df,fea)
    model_h,model_e=main(2,df,fea)
    Vth_h,Vth_e,model_Vth_h,model_Vth_e=main(4,df,fea)