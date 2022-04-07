import requests
import json
from copy import deepcopy
from collections import OrderedDict
import geopandas as gpd
import xarray as xr
import rioxarray as rxr
from pyproj import CRS
import pandas as pd
import os
import argparse
class WekeoPP:
    urlCredentials="https://wekeo-broker.apps.mercator.dpi.wekeo.eu/databroker/gettoken"
    ulrLicense="https://wekeo-broker.apps.mercator.dpi.wekeo.eu/databroker/termsaccepted/Copernicus_General_License"
    ulrCatalogue='https://wekeo-broker.apps.mercator.dpi.wekeo.eu/databroker/querymetadata/'
    urlRequest='https://wekeo-broker.apps.mercator.dpi.wekeo.eu/databroker/datarequest'
    urlOrder='https://wekeo-broker.apps.mercator.dpi.wekeo.eu/databroker/dataorder'
    NoLicense={'detail': 'Terms & conditions not accepted','status_code': 401,'title': 'Unauthorized'}
    Notoken={'detail': 'Missing or invalid token. Make sure your API invocation call has a header: "Authorization: Bearer ACCESS_TOKEN"','status_code': 403,'title': 'Forbidden'}
    UTM=gpd.read_file("./utmzone/utmzone.shp")
    def __init__(self, ID,password,tif=False):
        message=ID+":"+password
        import base64
        message_bytes = message.encode('ascii')
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode('ascii')
        self.credential=base64_message
        self.tif=tif
        
    def checkHandShake(self,r):
        try:
            test=json.loads(r.text)
        except:
            print(r.text)
            return r
        flagbad=True
        if test==self.NoLicense:
            self.AcceptLicense()
        elif test==self.Notoken:
            self.getAuth()
        else:
            flagbad=False
        #But all was good?
        if r.status_code!=200:
            print( test)
        return flagbad
            
    def Where(self,shapefile, tile=None, buffer=5000):
        self.buffer=buffer
        A=gpd.read_file(shapefile)
        assert A.crs.to_epsg()==4326
        self.shape=A
        zone=self.UTM[self.UTM.contains(A.iloc[0].geometry)].iloc[0].ZONE
        crsutm=CRS('+proj=utm +zone={ZONE} +datum=WGS84 +units=m +no_defs +type=crs'.format(ZONE=zone))
        Autm=A.to_crs(crsutm)
        Ab=Autm.buffer(self.buffer).to_crs(A.crs)
        minLong,minLat,maxLong, maxLat=A.bounds.values[0]
        self.bb=[minLong,minLat,maxLong, maxLat]
        if tile:
            self.tile=tile.split(",")
        else:
            self.tile=[""]
        
    def When(self,start, end):
        self.start=str(pd.to_datetime(start)).replace(" ","T")+"Z"
        self.end=str(pd.to_datetime(end)).replace(" ","T")+"Z"
        
    def What(self,datasetId, productType=[],productGroupId=[]):
        self.datasetId=datasetId
        self.productType=productType
        self.productGroupId=productGroupId
        
    def getAuth(self):
        r=requests.get(self.urlCredentials,headers={"authorization": 'Basic {credentials}'.format(credentials=self.credential)})
        print(r.text)
        self.Auth=json.loads(r.text)["access_token"]
        return self.Auth
        
    def AcceptLicense(self):
        r=requests.put(self.ulrLicense,
               headers={'accept': 'application/json',"authorization": self.Auth},data='accepted=true')
        return r
        
    def getCatalogue(self):
        rform=requests.get(self.urlRequest+'/querymetadata/{id}'.format(id=self.datasetId),
               headers={"authorization": self.Auth})
        print(rform)
        self.Details=json.loads(rform.text)
        return self.Details
        
    def BuildRequests(self):
        self.jrequest={
        "datasetId": self.datasetId,
            "boundingBoxValues": [
              { "name": "bbox", "bbox": self.bb }
            ],
        "dateRangeSelectValues": [
            {
              "name": "temporal_interval",
              "start": self.start,
              "end": self.end
            }
          ],
        "stringChoiceValues": [
            {
              "name": "productType",
              "value": "{productType}"
            },
            {
              "name": "productGroupId",
              "value": "{productGroupId}"
            }
          ],
        "stringInputValues": [
            {
              "name": "tileId",
              "value": "{tileId}"
              }
              ]
          }
        self.jrequest={
        "datasetId": self.datasetId,
            "boundingBoxValues": [
              { "name": "bbox", "bbox": self.bb }
            ],
        "dateRangeSelectValues": [
            {
              "name": "temporal_interval",
              "start": self.start,
              "end": self.end
            }
          ],
        "stringChoiceValues": [
            {
              "name": "productType",
              "value": self.productType
            },
            {
              "name": "productGroupId",
              "value": self.productGroupId
            }
          ]
          }
        self.jrequests=[]
        for prod in self.productType:
            #print("test")
            for group in self.productGroupId:
                for tile in self.tile:
                    temp=deepcopy(self.jrequest)
                    print(prod)
                    for y,x in enumerate(temp['stringChoiceValues']):
                        if x["name"]=='productType':
                            #print(prod,y)
                            temp['stringChoiceValues'][y]["value"]=prod
                    for y,x in enumerate(temp['stringChoiceValues']):
                        if x["name"]=='productGroupId':
                            temp['stringChoiceValues'][y]["value"]=group
                    #temp['stringChoiceValues'][0]["value"]=tile
                    self.jrequests.append(temp)
        
    def Search4Requests(self, JOBIDS=None):
        #Ask
        if JOBIDS is None:
            jobIds=[]
            for jr in self.jrequests:
                headers={}
                headers["content-type"]='application/json'
                headers["authorization"]=self.Auth
                flagbad=True
                while flagbad:
                    rr = requests.post(self.urlRequest,data = json.dumps(jr), headers=headers)
                    flagbad=self.checkHandShake(rr)
                jobIds.append(json.loads(rr.text)["jobId"])
        else:
            jobIds=JOBIDS
        #answer completed?
        ReadyId=[]
        NotReadyId=[]
        for jobId in jobIds:
            flagbad=True
            while flagbad:
                rstatus=requests.get(self.urlRequest+'/status/{id}'.format(id=jobId),
                       headers={"authorization": self.Auth })
                flagbad=self.checkHandShake(rstatus)
            if json.loads(rstatus.text)["status"]=="completed":
                ReadyId.append(jobId)
            else:
                NotReadyId.append(jobId)
        self.ReadyId=ReadyId
        #Is somebody left behind?
        NotNotReadyId=[]
        for jobId in NotReadyId:
            flagbad=True
            while flagbad:
                rstatus=requests.get(self.urlRequest+'/status/{id}'.format(id=jobId),
                       headers={"authorization": self.Auth })
                flagbad=self.checkHandShake(rstatus)
            if json.loads(rstatus.text)["status"]=="completed":
                ReadyId.append(jobId)
            else:
                print(rstatus.text)
                NotNotReadyId.append(jobId)
        self.ReadyId=ReadyId
        self.lost=NotNotReadyId
        #I want to see the answers
        Files=OrderedDict()
        for Id in ReadyId:
            files=[]
            flagbad=True
            while flagbad:
                rURL=requests.get(self.urlRequest+'/jobs/{id}/result?size=20&page=0'.format(id=Id),
                       headers={"authorization": self.Auth})
                flagbad=self.checkHandShake(rURL)
            files+=[x["url"] for x in json.loads(rURL.text)["content"]]
            pages=json.loads(rURL.text)["pages"]
            files=[x['url'] for x in json.loads(rURL.text)["content"]]
            for p in range(1,pages):
                flagbad=True
                while flagbad:
                    rURL=requests.get(self.urlRequest+'/jobs/{id}/result?size=20&page={page}'.format(id=Id,page=p),
                       headers={"authorization": self.Auth})
                    flagbad=self.checkHandShake(rURL)
                files+=[x["url"] for x in json.loads(rURL.text)["content"]]
            
            Files[Id]=files
        self.Files=Files
        #self.Files=sum([list(Files.values()),[]])
        #self.Files =sum([x for x in Q.Files.values()],[])
        return self.lost
        
    def checkIfAlreadyGotIt(self, pattern="QFLAG2",path="./"):
        QFLAG=[x for x in os.listdir(path) if x.find(pattern)>-1]
        FilesClean={}
        print("File to download",len(sum([x for x in self.Files.values()],[])))
        for k in self.Files:
            FilesClean[k]=[]
            for File in self.Files[k]:
                if File.split("/")[-1].replace(".tif",".nc") not in QFLAG:
                    FilesClean[k].append(File)
        self.Files=FilesClean
        print("afterclean")
        print(len(sum([x for x in self.Files.values()],[])))
    def Crop(self,nomefile,crs=None,buffer=5000):
        import xarray as xr
        A=self.shape
        temp=xr.open_rasterio(nomefile)
        if not crs:
            crs=temp.crs
        else:
            temp=temp.rio.reproject(crs)
        AA=A.to_crs(temp.crs)
        minx,miny,maxx,maxy=AA.buffer(buffer).total_bounds
        temp=temp.loc[:,maxy:miny,minx:maxx]
        if not self.tif:
            try:
                temp.coords["band"]=[pd.to_datetime(temp.TIFFTAG_DATETIME.split()[0], format="%Y:%m:%d")]
            except AttributeError:
                pass
            temp.to_netcdf(".".join(nomefile.split(".")[:-1])+".crop.nc")
        else:
            temp.rio.to_raster(".".join(nomefile.split(".")[:-1])+"crop.tif")
        os.remove(nomefile)
    def Download(self, orderIDClean):
        Waiting=[]
        for order in orderIDClean:
            flagbad=True
            while flagbad:
                rstatusOrder=requests.get(self.urlOrder+'/status/{id}'.format(id=order),
                       headers={"authorization": self.Auth})
                flagbad=self.checkHandShake(rstatusOrder)
            Status=json.loads(rstatusOrder.text)["status"]
            if Status!="completed":
                Waiting.append(order)
                print("Skip..")
                print(order)
            else:
                print("Download..")
                print(order)
                rdownload=requests.get(self.urlOrder+'/download/{id}'.format(id=order),
                       headers={"authorization": self.Auth})
                namefile=json.loads(rstatusOrder.text)["url"].split("/")[-1]
                open(namefile,"wb").write(rdownload.content)
                self.Crop(namefile)
        return Waiting
        
    def OrderAndDownload(self, Max=100,pattern="QFLAG2",path="./"):
        orderID=[]
        self.checkIfAlreadyGotIt(pattern=pattern,path=path)
        count=0
        for k in self.Files:
            for f in self.Files[k]:
                count+=1
                print("File Ordered: {count}".format(count=count))
                if count>Max:
                    break
                flagbad=True
                while flagbad:
                    #print("Hell")
                    rOrder=requests.post(self.urlOrder,
                       headers={"authorization": self.Auth,'content-type': 'application/json'}, 
                               data='{'+'"jobId":"{jobid}","uri":"{f}" '.format(f=f, jobid=k)+'}')
                    flagbad=self.checkHandShake(rOrder)
                orderID+=[[f,json.loads(rOrder.text)["orderId"]]] 
        self.orderIDClean=[x[1] for x in orderID]
        self.Waiting=self.Download(self.orderIDClean)
        return self.Waiting

if "__main__"==__name__:
    parser = argparse.ArgumentParser(description='WekeoPPget options', prog="eLTER")
    parser.add_argument("--login", dest="login", action="store", help=" json file where to recover user and password for the account on wekeo ")
    parser.add_argument("--tif", dest="tif", action="store_true", help=" add option if you want cutted element in tif format and not in netcdf4 ")
    parser.add_argument("--start", dest="start", action="store", help="start time e.g. '2022-12-01' or '2022-12-01 17:02:01' ")
    parser.add_argument("--end",   dest="end",  action="store", help="start time e.g. '2022-12-01' or '2022-12-01 17:02:01'")
    parser.add_argument("--shape", dest="shapefile", action="store", help=" path for the shapefile of region of interest in WGS84 projection")
    parser.add_argument("--buffer", dest="buffer",type=int, default=0, action="store", help=" buffer in meter around the shape")
    parser.add_argument("--tile", dest="tile", action="store", help="name of tile of interest")
    #parser.add_argument("--product", dest="datasetId" action="store", help=" write 'daily', 'yearly' or '10-daily"")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--yearly", dest="yearly", default=[],action="store", help=" write 'TPROD,...' see on wekeo url")
    group.add_argument("--daily", dest="daily", default="",action="store", help=" write a subset of this list 'PPI,NDVI,FAPAR,LAI,QFLAG'")
    group.add_argument("--10daily", dest="daily10", default="", action="store", help=" write 'PPI,QFLAG'")
    parser.add_argument("--seasons", dest="seasons", default="", action="store", help=" write a subset of this list  's1,s2'")
    DICT={"10daily":["EO:HRVPP:DAT:SEASONAL-TRAJECTORIES",["PPI","QFLAG"]],
          "yearly":["EO:HRVPP:DAT:VEGETATION-PHENOLOGY-AND-PRODUCTIVITY-PARAMETERS",['MAXV', 'SOSV', 'MAXD', 'EOSD', 'LSLOPE', 'MINV', 'RSLOPE','TPROD', 'EOSV', 'AMPL', 'LENGTH', 'SPROD', 'SOSD']],
          "daily":["EO:HRVPP:DAT:VEGETATION-INDICES",['PPI','NDVI','FAPAR','LAI','QFLAG']]}
    ARG=parser.parse_args()
    import json
    with open(ARG.login) as json_file:
        LOGIN = json.load(json_file)
    WK=WekeoPP(LOGIN["user"],LOGIN["password"], ARG.tif)
    WK.Where(ARG.shapefile, ARG.buffer)
    WK.When(ARG.start,ARG.end)
    if ARG.daily:
        datasetId, producttypeRef= DICT["daily"]
        productType=[x for x in ARG.daily.split(",") if x in producttypeRef]
        productGroupId=[""]
    elif ARG.yearly:
        datasetId, producttypeRef= DICT["yearly"]
        productType=[x for x in ARG.yearly.split(",") if x in producttypeRef]
        productGroupId=ARG.seasons.split()
    elif ARG.daily10:
        datasetId, producttypeRef= DICT["10daily"]
        productType=[x for x in ARG.daily10.split(",") if x in producttypeRef]
        productGroupId=[""]
    WK.What(datasetId=datasetId,productType=productType,productGroupId=productGroupId)
    WK.getAuth()
    WK.AcceptLicense()
    WK.BuildRequests()
    print(WK.jrequest)
    #print(WK.jrequests)
    WK.Search4Requests()
    #print(WK.Files)
    Waiting=WK.OrderAndDownload()
    if Waiting:
        Waiting=WK.Download(Waiting)
        print("File not yet available:", Waiting)
    
