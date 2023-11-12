from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="OK"), 200


@app.route("/count", methods=["GET"])
def count():
    """Return the count of documents in the 'songs' collection."""
    count = db.songs.count_documents({})
    return jsonify(count=count), 200


@app.route("/song", methods=["GET"])
def songs():
    songs_data = list(db.songs.find({}))
    formatted_songs = [{"_id": str(song["_id"]), "id": song["id"], "lyrics": song["lyrics"], "title": song["title"]} for song in songs_data]

    return jsonify(songs=formatted_songs), 200


@app.route("/song/<int:song_id>", methods=["GET"])
def get_song_by_id(song_id):
    song = db.songs.find_one({"id": song_id})

    if song is None:
        return jsonify({"message": f"Song with id {song_id} not found"}), 404

    formatted_song = {
        "_id": str(song["_id"]),
        "id": song["id"],
        "lyrics": song["lyrics"],
        "title": song["title"]
    }

    return jsonify(song=formatted_song), 200

@app.route("/song", methods=["POST"])
def create_song():
    # Extract song data from the request body
    song_data = request.get_json()

    # Check if the song with the given ID already exists
    existing_song = db.songs.find_one({"id": song_data["id"]})
    if existing_song:
        return jsonify({"Message": f"Song with id {song_data['id']} already present"}), 302

    # Insert the new song into the database
    result = db.songs.insert_one(song_data)
    
    # Return the ID of the inserted song
    return jsonify({"inserted id": str(result.inserted_id)}), 201

@app.route("/song/<int:song_id>", methods=["PUT"])
def update_song(song_id):
    # Extract updated song data from the request body
    updated_song_data = request.get_json()

    # Find the song in the database
    existing_song = db.songs.find_one({"id": song_id})
    if existing_song is None:
        return jsonify({"message": "Song not found"}), 404

    # Check if the incoming data is the same as the existing data
    if existing_song["lyrics"] == updated_song_data.get("lyrics", "") and existing_song["title"] == updated_song_data.get("title", ""):
        return jsonify({"message": "Song found, but nothing updated"}), 200

    # Update the song with the incoming request data
    db.songs.update_one({"id": song_id}, {"$set": updated_song_data})

    # Return the updated song data
    updated_song = db.songs.find_one({"id": song_id})
    formatted_updated_song = {
        "_id": str(updated_song["_id"]),
        "id": updated_song["id"],
        "lyrics": updated_song["lyrics"],
        "title": updated_song["title"]
    }

    return jsonify(updated_song=formatted_updated_song), 200

@app.route("/song/<int:song_id>", methods=["DELETE"])
def delete_song(song_id):
    # Use db.songs.delete_one method to delete the song from the database
    result = db.songs.delete_one({"id": song_id})

    # Check the deleted_count attribute of the result
    if result.deleted_count == 0:
        return jsonify({"message": "Song not found"}), 404
    else:
        # Song was successfully deleted
        return "", 204