import base64
import os
import time
import json
import re
import requests

from download import utils


def generate_api_key(username, password):
    """ 
    Generates a Base64-encoded api key, based on the WEkEO user 
    credentials username:password.
    
    Parameters:
        username: WEkEO username
        password: WEkEO password
    
    Returns:
        Returns a string of the Base64-encoded api key
    """
    s = username + ':' + password
    return (base64.b64encode(str.encode(s), altchars=None)).decode()


def init(dataset_id, api_key, download_dir_path):
    """ 
    Initiates a dictionary with keys needed to use the HDA API.
    
    Parameters:
        dataset_id: String representing the WEkEO collection id
        api_key: Base64-encoded string
        download_dir_path: directory path where data shall be downloaded 
                           to
    
    Returns:
        Returns the initiated dictionary.
    """
    hda_dict = {}
    # Data broker address
    hda_dict["broker_endpoint"] = \
        "https://wekeo-broker.apps.mercator.dpi.wekeo.eu/databroker"
    # Terms and conditions
    hda_dict["acceptTandC_address"] \
        = hda_dict["broker_endpoint"] \
          + "/termsaccepted/Copernicus_General_License"
    # Access-token address
    hda_dict["accessToken_address"] = hda_dict["broker_endpoint"] \
                                      + '/gettoken'
    # Dataset id
    hda_dict["dataset_id"] = dataset_id
    # API key
    hda_dict["api_key"] = api_key

    # set HTTP success code
    hda_dict["CONST_HTTP_SUCCESS_CODE"] = 200

    # download directory
    hda_dict["download_dir_path"] = download_dir_path
    if not os.path.exists(download_dir_path):
        os.makedirs(download_dir_path)

    return hda_dict


def get_access_token(hda_dict, bluecloud_proxy=True):
    """ 
    Requests an access token to use the HDA API and stores it as separate
    key in the dictionary
    
    Parameters:
        hda_dict: dictionary initied with the function init, that stores 
        all required information to be able to interact with the HDA API.
    
    Returns:
        Returns the dictionary including the access token
        @param bluecloud_proxy: request token using bluecloud proxy
    """

    if bluecloud_proxy:
        hda_dict['access_token'] = get_token_from_bluecloud_proxy()
    else:
        hda_dict['access_token'] = get_token_from_wekeo(hda_dict)
    hda_dict['headers'] = {'Authorization': 'Bearer ' + hda_dict["access_token"], 'Accept': 'application/json'}
    return hda_dict


def get_token_from_wekeo(hda_dict):
    headers = {
        'Authorization': 'Basic ' + hda_dict['api_key']
    }
    print("Getting an access token. This token is valid for one hour only.")
    response = requests.get(hda_dict['accessToken_address'], headers=headers, verify=False)

    # If the HTTP response code is 200 (i.e. success), then retrive the
    # token from the response
    if response.status_code == hda_dict["CONST_HTTP_SUCCESS_CODE"]:
        access_token = json.loads(response.text)['access_token']
        print("Success: Access token is " + access_token)
        return access_token
    else:
        print(response.headers)
        raise Exception("Error: Unexpected response {}".format(response))


def get_token_from_bluecloud_proxy():
    from download import utils

    globalVariablesFile = os.path.dirname(__file__).split('download')[0] + '/globalvariables.csv'
    gcubeToken = utils.get_gcube_token(globalVariablesFile)

    hprops = {"Accept": "application/json"}
    urlString = "https://data.d4science.org/wekeo/gettoken?gcube-token=" + gcubeToken
    r = requests.get(urlString, headers=hprops)
    if r.status_code != 200:
        error = "Error in Get Token {} {}".format(r.status_code, r.text)
        print(error)
        raise Exception(error)
    t = json.loads(r.text)
    token = t["access_token"]
    print("Token:", token)
    return token

def query_metadata(hda_dict):
    """ 
    Requests metadata for the given dataset id and stores the response 
    of the request in the dictionary.
    
    Parameters:
        hda_dict: dictionary initied with the function init, that stores 
        all required information to be able to interact with the HDA API
    
    Returns:
        Returns the dictionary including the query response
    """
    response = requests.get(hda_dict['broker_endpoint'] + \
                            '/querymetadata/' + hda_dict['dataset_id'], \
                            headers=hda_dict['headers'])

    print('Getting query metadata, URL Is ' + hda_dict['broker_endpoint'] \
          + '/querymetadata/' + hda_dict['dataset_id'] \
          + "?access_token=" + hda_dict['access_token'])
    print("************** Query Metadata for " + hda_dict['dataset_id'] \
          + " **************")

    if (response.status_code == hda_dict['CONST_HTTP_SUCCESS_CODE']):
        parsedResponse = json.loads(response.text)
        print(json.dumps(parsedResponse, indent=4, sort_keys=True))
        print("**************************************************")
    else:
        print("Error: Unexpected response {}".format(response))

    hda_dict['parsedResponse'] = parsedResponse
    return hda_dict


def acceptTandC(hda_dict):
    """ 
    Checks if the Terms and Conditions have been accepted and it not, 
    they will be accepted. The response is stored in the dictionary
    
    Parameters:
        hda_dict: dictionary initied with the function init, that stores 
                  all required information to be able to interact with 
                  the HDA API
    
    Returns:
        Returns the dictionary including the response from the Terms and 
        Conditions statement.
    """

    msg1 = "Accepting Terms and Conditions of Copernicus_General_License"
    msg2 = "Copernicus_General_License Terms and Conditions already accepted"
    response = requests.get(hda_dict['acceptTandC_address'], headers=hda_dict['headers'])

    isTandCAccepted = json.loads(response.text)['accepted']

    if isTandCAccepted is False:
        print(msg1)
        response = requests.put(hda_dict['acceptTandC_address'], headers=hda_dict['headers'])
    else:
        print(msg2)
    isTandCAccepted = json.loads(response.text)['accepted']
    hda_dict['isTandCAccepted'] = isTandCAccepted
    return hda_dict


def get_job_id(hda_dict, data):
    """ 
    Assigns a job id for the data request.
    
    Parameters:
        hda_dict: dictionary initied with the function init, 
                  that stores all required information to be able to 
                  interact with the HDA API
        data: dictionary containing the dataset description

    Returns:
        Returns the dictionary including the assigned job id.
    """
    response = requests.post(hda_dict['broker_endpoint'] + '/datarequest', headers=hda_dict['headers'], json=data,
                             verify=False)

    if response.status_code == hda_dict['CONST_HTTP_SUCCESS_CODE']:
        job_id = json.loads(response.text)['jobId']
        print("Query successfully submitted. Job ID is " + job_id)
    else:
        job_id = ""
        print("Error: Unexpected response {}".format(response))

    hda_dict['job_id'] = job_id
    get_request_status(hda_dict)
    return hda_dict


def get_request_status(hda_dict):
    """ 
    Requests the status of the process to assign a job ID.
    
    Parameters:
        hda_dict: dictionary initied with the function init, that 
                  stores all required information to be able to 
                  interact with the HDA API
    """
    status = "not started"
    start_time = time.time()
    timeout = 120
    count = 0
    while status != "completed":
        count = count + 1
        if count > 20:
            print('Waiting 5 seconds...')
            time.sleep(5)
        response = requests.get(hda_dict['broker_endpoint'] + '/datarequest/status/' + hda_dict['job_id'],
                                headers=hda_dict['headers'])
        if response.status_code == hda_dict['CONST_HTTP_SUCCESS_CODE']:
            status = json.loads(response.text)['status']
            if 'fail' not in status:
                print("Query successfully submitted. Status is " + status)
            else:
                message = json.loads(response.text)['message']
                raise Exception("Query has failed with message: ", message)
        else:
            raise Exception("Error: Unexpected response {}".format(response))

        if time.time() - start_time > timeout:
            raise Exception("ERROR: Timeout reached")


def get_results_list(hda_dict):
    """ 
    Generates a list of filenames to be available for download
    
    Parameters:
        hda_dict: dictionary initied with the function init, that 
                  stores all required information to be able to interact
                  with the HDA API

    Returns:
        Returns the dictionary including the list of filenames to be 
        downloaded.
    """
    params = {'page': '0', 'size': '5'}
    response = requests.get(hda_dict['broker_endpoint'] + \
                            '/datarequest/jobs/' + hda_dict['job_id'] + \
                            '/result', headers=hda_dict['headers'], params=params)
    results = json.loads(response.text)
    hda_dict['results'] = results

    print("************** Results *******************************")
    print(json.dumps(results, indent=4, sort_keys=True))
    print("*******************************************")

    return hda_dict


def get_order_ids(hda_dict):
    """ 
    Assigns each file to be downloaded a unique order ID.
    
    Parameters:
        hda_dict: dictionary initied with the function init, that 
                  stores all required information to be able to 
                  interact with the HDA API

    Returns:
        Returns the dictionary including the list of order IDs and the
        request status of assigning the order IDs.
    """
    i = 0
    order_ids = []
    order_sizes = []

    for result in hda_dict['results']['content']:

        data = {
            "jobId": hda_dict['job_id'],
            "uri": result['url']
        }

        order_sizes.append(result['size'])

        response = requests.post(hda_dict['broker_endpoint'] + \
                                 '/dataorder', headers=hda_dict['headers'], \
                                 json=data, verify=False)

        if (response.status_code == hda_dict['CONST_HTTP_SUCCESS_CODE']):
            order_ids.append(json.loads(response.text)['orderId'])
            print("Query successfully submitted. Order ID is " + \
                  order_ids[i])
            response = get_order_status(hda_dict, order_ids[i])
        else:
            print("Error: Unexpected response {}".format(response))

        i += 1
    hda_dict['order_ids'] = order_ids
    hda_dict['order_sizes'] = order_sizes
    hda_dict['order_status_response'] = response
    return hda_dict


def get_order_status(hda_dict, order_id):
    """ 
    Requests the status of assigning an order ID for a data file.
    
    Parameters:
        hda_dict: dictionary initied with the function init, that 
                  stores all required information to be able to 
                  interact with the HDA API
        order_id: the order id for the data file

    Returns:
        Returns the response of assigning an order ID.
    """
    status = "not started"
    count = 0
    while (status != "completed"):
        count = count + 1
        if count > 20:
            print('Waiting 5 seconds...')
            time.sleep(5)
        response = requests.get(hda_dict['broker_endpoint'] + \
                                '/dataorder/status/' + order_id, \
                                headers=hda_dict['headers'])

        if (response.status_code == hda_dict['CONST_HTTP_SUCCESS_CODE']):
            status = json.loads(response.text)['status']
            print("Query successfully submitted. Status is " + status)
        else:
            print("Error: Unexpected response {}".format(response))

    return response


def downloadFileMemory(url, headers, file_name):
    import netCDF4
    r = requests.get(url, headers=headers, stream=True)

    if r.status_code == 200:
        nc_dataset = netCDF4.Dataset(file_name, mode='r', memory=r.content)
        return nc_dataset
    else:
        raise Exception('Download error, status code: ' + str(r.status_code))


def downloadFile(url, headers, directory, file_name, total_length=0, dl_status=False):
    """ 
    Function to download a a single data file.
    
    Parameters:
        url: is the download url which included the unique order ID
        headers:
        directory: download directory, where data file shall be stored
        file_name: name of the data file
        
    Returns:
        Returns the time needed to download the data file.
    """
    r = requests.get(url, headers=headers, stream=True)
    if r.status_code == 200:
        filename = os.path.join(directory, file_name)
        print("Downloading " + filename)
        with open(filename, 'wb') as f:
            start = time.process_time()
            print("File size is: %8.2f MB" % (total_length / (1024 * 1024)))
            dl = 0
            for chunk in r.iter_content(64738):
                dl += len(chunk)
                f.write(chunk)
                if dl_status:
                    utils.show_dl_percentage(dl, start, total_length)
            try:
                print("[%8.2f] MB downloaded, %8.2f kbps" \
                      % (dl / (1024 * 1024), (dl / (time.process_time() - start)) / 1024))
            except:
                pass
        print("File downloaded")
        print("Apply mask to nan value")
        # mask_nc_file(filename=filename)

        return time.process_time() - start


dimensionVar = ['time_counter', 'nav_lon', 'nav_lat', 'deptht', 'tbnds', 'time_counter_bnds',
                'depth', 'lon', 'lat', 'longitude', 'latitude', 'time']


def mask_nc_file(filename):
    import netCDF4
    import numpy as np
    print('Fix mask to file: ', filename)
    nc_dataset = netCDF4.Dataset(filename, 'r+')

    for nc_var in nc_dataset.variables:
        if nc_var not in dimensionVar:
            if not np.ma.is_masked(nc_dataset[nc_var]):
                nc_dataset[nc_var][:] = np.ma.masked_invalid(nc_dataset[nc_var])

    nc_dataset.close()


def get_filename_from_cd(cd):
    """
    Get the filename from content disposition
    
    Parameters:
        cd : content disposition (from https://www.w3.org/Protocols/
            rfc2616/rfc2616-sec19.html). The Content-Disposition 
            response-header field has been proposed as a means for 
            the origin server to suggest a default filename if the 
            user requests that the content is saved to a file. 
            This usage is derived from the definition of 
            Content-Disposition in RFC 1806 [35].

    Returns:
        The filename from content disposition (cd)
    """
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0][2:-1]


def get_filenames(hda_dict):
    """ 
    Generates a list of filenames taken from the results dictionary, 
    retrieved with the function request_results_list.
    
    Parameters:
        hda_dict: dictionary initied with the function init, that 
                  stores all required information to be able to 
                  interact with the HDA API

    Returns:
        Returns a list of filenames for each entry stored in the 
        dictionary returned by the function request_results_list.
    """
    fileName = []
    for file in hda_dict['results']['content']:
        fileName.append(file['filename'])
    return fileName


def download_data(hda_dict, file_extension=None, user_filename=None, in_memory=None, dl_status=False):
    """ 
    Downloads for each of the order IDs the associated data file.
    
    Parameters:
        hda_dict: dictionary initied with the function init, that 
                  stores all required information to be able to 
                  interact with the HDA API
        file_extension: 
                  optional file extension to add to file
        user_filename:  
                  user specified download name
        
    Returns:
        hda_dict: with names/paths of downloaded files
    """
    fileNames = []
    fileName = get_filenames(hda_dict)
    i = 0
    for order_id in hda_dict['order_ids']:
        if user_filename:
            file_name = user_filename
        else:
            file_name = fileName[i]

        if file_extension:
            file_name = file_name + file_extension

        download_url = hda_dict['broker_endpoint'] + '/dataorder/download/' + order_id

        product_size = hda_dict['order_sizes'][i]

        if in_memory:
            time_elapsed = downloadFileMemory(download_url, hda_dict['headers'], file_name)
        else:
            time_elapsed = downloadFile(download_url, hda_dict['headers'],
                                        hda_dict['download_dir_path'], file_name,
                                        product_size,
                                        dl_status=dl_status)

        fileNames.append(os.path.join(hda_dict['download_dir_path'], file_name))

        print("Download/Request complete...")
        print("Time Elapsed: " + str(time_elapsed) + " seconds")
        response = hda_dict['order_status_response']

        if response.status_code == hda_dict['CONST_HTTP_SUCCESS_CODE']:
            order_file = "./" + file_name
            if os.path.isfile(order_file):
                print("Query successfully submitted. Response is {}" \
                      .format(response))
        else:
            print("Error: Unexpected response {}".format(response))

        i += 1

    hda_dict['filenames'] = fileNames
    return hda_dict
