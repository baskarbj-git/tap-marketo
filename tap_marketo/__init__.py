import pendulum
import singer
from singer import bookmarks

from tap_marketo.client import Client
from tap_marketo.discover import discover
from tap_marketo.sync import sync
from singer.bookmarks import (
    get_bookmark,
    write_bookmark,
    get_currently_syncing,
    set_currently_syncing,
)

REQUIRED_CONFIG_KEYS = [
    "start_date",

    # Log in to Marketo
    # Go to Admin, select Integration->Web Services
    # Endpoint url matches https://123-ABC-456.mktorest.com/rest
    # Domain is the 9 character alpha numeric part of the url
    "domain",

    # Log in to Marketo
    # Go to Admin, select Integration->Launch Point
    # Client ID and Secret can be found by clicking "View Details"
    "client_id",
    "client_secret",
]


def validate_state(config, catalog, state):
    for stream in catalog["streams"]:
        if not stream["schema"].get("selected"):
            # If a stream is deselected while it's the current stream, unset the
            # current stream.
            if stream["tap_stream_id"] == get_currently_syncing(state):
                set_currently_syncing(state, None)
            continue

        if not stream.get("replication_key"):
            continue

        # If there's no bookmark for a stream (new integration, newly selected,
        # reset, etc) we need to use the default start date from the config.
        bookmark = get_bookmark(state,
                                stream["tap_stream_id"],
                                stream["replication_key"])
        if bookmark is None:
            state = write_bookmark(state,
                                   stream["tap_stream_id"],
                                   stream["replication_key"],
                                   config["start_date"])

    singer.write_state(state)
    return state

def _main(config, properties, state, discover_mode=False):
    client = Client(**config)
    if discover_mode:
        discover(client)
    elif properties:
        state = validate_state(config, properties, state)
        sync(client, properties, state)
    else:
        pass


def main():
    args = singer.utils.parse_args(REQUIRED_CONFIG_KEYS)

    try:
        _main(args.config, args.properties, args.state, args.discover)
    except Exception as e:
        singer.log_critical(e)
        raise e


if __name__ == "__main__":
    main()
