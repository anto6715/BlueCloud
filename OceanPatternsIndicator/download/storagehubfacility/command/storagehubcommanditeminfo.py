#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @author: Giancarlo Panichi
#
# Created on 2018/06/15 
# 
import requests
from .storagehubcommand import StorageHubCommand


class StorageHubCommandItemInfo(StorageHubCommand):     

    def __init__(self, itemId, gcubeToken, storageHubUrl, destinationFile): 
        self.itemId=itemId
        self.gcubeToken = gcubeToken
        self.storageHubUrl = storageHubUrl
        self.destinationFile = destinationFile
       
        
    def execute(self):
        print("Execute StorageHubCommandItemInfo")
        print(self.storageHubUrl + "/items/" + self.itemId + "/?exclude=hl:accounting");
        
        urlString = self.storageHubUrl + "/items/" + self.itemId + "/?exclude=hl:accounting&gcube-token=" + self.gcubeToken
        r = requests.get(urlString)
        print(r.status_code)
        if r.status_code != 200:
            print("Error in execute StorageHubCommandItemInfo: " + r.status_code)
            raise Exception("Error in execute StorageHubCommandItemInfo: " + r.status_code)
        with open(self.destinationFile, 'w') as file:
            file.write(r.text)
    

    def __str__(self): 
        return 'StorageHubCommandItemInfo[itemId='+self.itemId+', storageHubUrl=' + str(self.storageHubUrl) + ', destinationFile=' + self.destinationFile + ']' 
