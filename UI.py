import PySimpleGUI as sg
import csv
import os
import xmltodict
import http.client
import json
from dotenv import load_dotenv

# need to sort out working directories.
working_directory = os.getcwd()


def configure():
    """Configures env vars from .env file."""
    load_dotenv()


def convert_csv_array(csv_address):
    """Receives a .csv file and parses it. Returns a list of numbers."""

    file = open(csv_address)
    csv_reader = csv.reader(file)
    header = next(csv_reader)   # Skipping columns names if any.
    rows = []
    for row in csv_reader:
        rows.append(row)
    file.close()
    return rows


sg.theme("DarkAmber")
layout = [
            [sg.Text("Choose a CSV file with Numbers to cancel:")],
            [sg.InputText(size=(60, 15), key="-FILE_PATH-"),
             sg.FileBrowse(initial_folder=working_directory, file_types=[("CSV Files", "*.csv")])],
            [sg.Output(size=(67, 15))],
            [sg.Button('Submit .csv'), sg.Exit(), sg.Button('Cancel DIDs')]
        ]

window = sg.Window("Voxbone Cancellation Tool v0.4", layout)


filtered_list = []
dids_to_delete = []

while True:
    configure()
    event, values = window.read()
    if event in (sg.WIN_CLOSED, 'Exit'):
        break

    elif event == "Submit .csv" and not values["-FILE_PATH-"]:
        print("No .csv file submitted. Please select a .csv file and submit again.")

    elif event == "Submit .csv":
        csv_address = values["-FILE_PATH-"]
        new_nums = convert_csv_array(csv_address)
        for i in new_nums:
            phone = ''.join(i).replace("[,],'", "")
            if phone in filtered_list or not phone or len(phone) > 15:
                continue
            else:
                filtered_list.append(phone)
        print("List of read DID numbers:")
        print(filtered_list)
        print("Total numbers:" + str(len(filtered_list)) + "\n")

        for i in filtered_list:
            conn = http.client.HTTPSConnection(os.getenv("stg_url"))
            payload = ''
            headers = {
                "apikey":
                    os.getenv("stg_apikey")
            }
            conn.request("GET", "/v1/inventory/did?pageNumber=0&pageSize=200&e164Pattern="+i, payload, headers)
            res = conn.getresponse()
            data = res.read()
            result = xmltodict.parse(data.decode("utf-8"))
            conn.close()
            # Need to add cancellationDate key to the numbers
            # print(result)
            try:
                for key1, val1 in result.items():
                    dids_dict = val1["dids"]
                    if dids_dict["didId"] in dids_to_delete:
                        continue
                    else:
                        dids_to_delete.append(dids_dict["didId"])
            except KeyError:
                print("There is no number " + i + " in the Voxbone inventory, so that we can't find an ID for it.\n"
                                                  "Skipping...")
                continue
        if not dids_to_delete:
            print("We can't find any IDs to delete. Check the numbers list.")
        else:
            print("List of DID IDs that are going to be cancelled:")
            print(dids_to_delete)
            print("Total IDs: "+str(len(dids_to_delete)) + "\n")
            print("Press 'Cancel DIDs' to cancel all the numbers in the list. ")

    elif event == "Cancel DIDs" and not dids_to_delete:
        print("Nothing to do. Please submit a .csv file first.")

    elif event == "Cancel DIDs":
        print("Processing your request...")
        conn = http.client.HTTPSConnection(os.getenv("stg_url"))
        payload = json.dumps({
            "didIds": dids_to_delete
        })
        headers = {
            "apikey":
                os.getenv("stg_apikey"),
            "Content-Type": "application/json"
        }
        conn.request("POST", "/v1/ordering/cancel", payload, headers)
        res = conn.getresponse()
        data = res.read()
        result = xmltodict.parse(data.decode("utf-8"))
        conn.close()
        try:
            for key1, val1 in result.items():
                deleted = val1["numberCancelled"]
                print("Amount of numbers deleted: "+deleted)
                dids_to_delete = []
                filtered_list = []
        except KeyError:
            print("There are no numbers to delete.")

window.close()
