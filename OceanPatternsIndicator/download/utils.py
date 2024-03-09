import time


def get_field(type_file):
    """
    @param type_file: String that represent the file type
    @return: return the field associated to the input_file as cf standard name
    """
    import os
    import json
    actual_dir = os.path.dirname(__file__)
    with open(actual_dir + '/config/filename.json') as json_file:
        filename = json.load(json_file)
    field = None
    for type_file_tmp, fields_tmp in filename.items():
        if type_file == type_file_tmp:
            field = fields_tmp
            break
    if field is None:
        raise Exception("Can't assign a type file for type_file: " + str(type_file))
    return field


def get_type_file(field):
    """
    @param field: cf standard name used to represent a variable
    @return: return the type file associated to field indicated
    """
    import os
    import json
    actual_dir = os.path.dirname(__file__)
    with open(actual_dir + '/config/filename.json') as json_file:
        filename = json.load(json_file)

    type_file = None
    for type_file_tmp, fields_tmp in filename.items():
        if field in fields_tmp:
            type_file = type_file_tmp
            break
    if type_file is None:
        raise Exception("Can't assign an output type file for field: " + str(field))
    return type_file


def init_dl_dir(outdir=None):
    """
    If not exists, create the download dir
    @return: the path of default download directory
    """
    import os

    if outdir is None:
        outdir = os.path.dirname(__file__).split('download')[0] + '/indir'
    # create new dir called 'indir' in the parent directory of daccess module
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    return outdir


def get_gcube_token(globalVariablesFile):
    import os

    gcubeToken = None
    envs = os.environ

    if os.path.exists(globalVariablesFile):
        print(f"Reading gcube_token from {globalVariablesFile}")
        with open(globalVariablesFile) as fp:
            for line in fp:
                if line.find("gcube_token") != -1:
                    tk = line[14:]
                    gcubeToken = tk.replace('"', '').strip()
                    # print("Found gcube_token")
                    break
    elif 'GCUBE_TOKEN' in envs:  # when a method is executed in the dataminer
        print(f"Reading gcube_token from 'GCUBE_TOKEN' variables")
        gcubeToken = os.environ.get('GCUBE_TOKEN')
    else:
        raise Exception('Error gcube_token not found!')

    if gcubeToken is None:
        raise Exception("Some error occurs when try to read gcube_token!")

    return gcubeToken


def show_dl_percentage(dl, start, total_length):
    if total_length is not None:  # no content length header
        done = int(50 * dl / total_length)
        try:
            print("\r[%s%s]  %8.2f Mbps" % ('=' * done, ' ' * (50 - done),
                                            (dl / (time.process_time() - start)) / (1024 * 1024)), end='',
                  flush=True)
        except:
            pass
    else:
        if dl % 1024 == 0:
            try:
                print("[%8.2f] MB downloaded, %8.2f kbps" \
                      % (dl / (1024 * 1024), (dl / (time.process_time() - start)) / 1024))
            except:
                pass