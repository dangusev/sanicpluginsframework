import inspect
import os
from time import gmtime, strftime
import pytest
from spf import SanicPlugin


class TestPlugin(SanicPlugin):
    pass

# The following tests are taken directly from Sanic source @ v0.8.2
# and modified to test the SanicPlugin, rather than Sanic

# ------------------------------------------------------------ #
#  GET
# ------------------------------------------------------------ #

@pytest.fixture(scope="module")
def static_file_directory():
    """The static directory to serve"""
    current_file = inspect.getfile(inspect.currentframe())
    current_directory = os.path.dirname(os.path.abspath(current_file))
    static_directory = os.path.join(current_directory, "static")
    return static_directory


def get_file_path(static_file_directory, file_name):
    return os.path.join(static_file_directory, file_name)


def get_file_content(static_file_directory, file_name):
    """The content of the static file to check"""
    with open(get_file_path(static_file_directory, file_name), "rb") as file:
        return file.read()


@pytest.fixture(scope="module")
def large_file(static_file_directory):
    large_file_path = os.path.join(static_file_directory, "large.file")

    size = 2 * 1024 * 1024
    with open(large_file_path, "w") as f:
        f.write("a" * size)

    yield large_file_path

    os.remove(large_file_path)


@pytest.fixture(autouse=True, scope="module")
def symlink(static_file_directory):
    src = os.path.abspath(
        os.path.join(os.path.dirname(static_file_directory), "conftest.py")
    )
    symlink = "symlink"
    dist = os.path.join(static_file_directory, symlink)
    os.symlink(src, dist)
    yield symlink
    os.remove(dist)


@pytest.fixture(autouse=True, scope="module")
def hard_link(static_file_directory):
    src = os.path.abspath(
        os.path.join(os.path.dirname(static_file_directory), "conftest.py")
    )
    hard_link = "hard_link"
    dist = os.path.join(static_file_directory, hard_link)
    os.link(src, dist)
    yield hard_link
    os.remove(dist)


@pytest.mark.parametrize(
    "file_name",
    ["test.file", "decode me.txt", "python.png", "symlink", "hard_link"],
)
def test_static_file(spf, static_file_directory, file_name):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file", get_file_path(static_file_directory, file_name)
    )
    spf.register_plugin(plugin)
    request, response = app.test_client.get("/testing.file")
    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)


@pytest.mark.parametrize("file_name", ["test.html"])
def test_static_file_content_type(spf, static_file_directory, file_name):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        content_type="text/html; charset=utf-8",
    )
    spf.register_plugin(plugin)
    request, response = app.test_client.get("/testing.file")
    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"


@pytest.mark.parametrize(
    "file_name", ["test.file", "decode me.txt", "symlink", "hard_link"]
)
@pytest.mark.parametrize("base_uri", ["/static", "", "/dir"])
def test_static_directory(spf, file_name, base_uri, static_file_directory):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(base_uri, static_file_directory)
    spf.register_plugin(plugin)
    request, response = app.test_client.get(
        uri="{}/{}".format(base_uri, file_name)
    )
    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_head_request(spf, file_name, static_file_directory):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    request, response = app.test_client.head("/testing.file")
    assert response.status == 200
    assert "Accept-Ranges" in response.headers
    assert "Content-Length" in response.headers
    assert int(response.headers["Content-Length"]) == len(
        get_file_content(static_file_directory, file_name)
    )


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_correct(spf, file_name, static_file_directory):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    headers = {"Range": "bytes=12-19"}
    request, response = app.test_client.get("/testing.file", headers=headers)
    assert response.status == 206
    assert "Content-Length" in response.headers
    assert "Content-Range" in response.headers
    static_content = bytes(get_file_content(static_file_directory, file_name))[
        12:20
    ]
    assert int(response.headers["Content-Length"]) == len(static_content)
    assert response.body == static_content


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_front(spf, file_name, static_file_directory):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    headers = {"Range": "bytes=12-"}
    request, response = app.test_client.get("/testing.file", headers=headers)
    assert response.status == 206
    assert "Content-Length" in response.headers
    assert "Content-Range" in response.headers
    static_content = bytes(get_file_content(static_file_directory, file_name))[
        12:
    ]
    assert int(response.headers["Content-Length"]) == len(static_content)
    assert response.body == static_content


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_back(spf, file_name, static_file_directory):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    headers = {"Range": "bytes=-12"}
    request, response = app.test_client.get("/testing.file", headers=headers)
    assert response.status == 206
    assert "Content-Length" in response.headers
    assert "Content-Range" in response.headers
    static_content = bytes(get_file_content(static_file_directory, file_name))[
        -12:
    ]
    assert int(response.headers["Content-Length"]) == len(static_content)
    assert response.body == static_content


@pytest.mark.parametrize("use_modified_since", [True, False])
@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_empty(
    spf, file_name, static_file_directory, use_modified_since
):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
        use_modified_since=use_modified_since,
    )
    spf.register_plugin(plugin)
    request, response = app.test_client.get("/testing.file")
    assert response.status == 200
    assert "Content-Length" in response.headers
    assert "Content-Range" not in response.headers
    assert int(response.headers["Content-Length"]) == len(
        get_file_content(static_file_directory, file_name)
    )
    assert response.body == bytes(
        get_file_content(static_file_directory, file_name)
    )


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_error(spf, file_name, static_file_directory):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    headers = {"Range": "bytes=1-0"}
    request, response = app.test_client.get("/testing.file", headers=headers)
    assert response.status == 416
    assert "Content-Length" in response.headers
    assert "Content-Range" in response.headers
    assert response.headers["Content-Range"] == "bytes */%s" % (
        len(get_file_content(static_file_directory, file_name)),
    )


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_invalid_unit(
    spf, file_name, static_file_directory
):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    unit = "bit"
    headers = {"Range": "{}=1-0".format(unit)}
    request, response = app.test_client.get("/testing.file", headers=headers)

    assert response.status == 416
    assert response.text == "Error: {} is not a valid Range Type".format(unit)


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_invalid_start(
    spf, file_name, static_file_directory
):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    start = "start"
    headers = {"Range": "bytes={}-0".format(start)}
    request, response = app.test_client.get("/testing.file", headers=headers)

    assert response.status == 416
    assert response.text == "Error: '{}' is invalid for Content Range".format(
        start
    )


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_invalid_end(
    spf, file_name, static_file_directory
):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    end = "end"
    headers = {"Range": "bytes=1-{}".format(end)}
    request, response = app.test_client.get("/testing.file", headers=headers)

    assert response.status == 416
    assert response.text == "Error: '{}' is invalid for Content Range".format(
        end
    )


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_invalid_parameters(
    spf, file_name, static_file_directory
):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    spf.register_plugin(plugin)
    headers = {"Range": "bytes=-"}
    request, response = app.test_client.get("/testing.file", headers=headers)

    assert response.status == 416
    assert response.text == "Error: Invalid for Content Range parameters"


@pytest.mark.parametrize(
    "file_name", ["test.file", "decode me.txt", "python.png"]
)
def test_static_file_specified_host(spf, static_file_directory, file_name):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        host="www.example.com",
    )
    spf.register_plugin(plugin)
    headers = {"Host": "www.example.com"}
    request, response = app.test_client.get("/testing.file", headers=headers)
    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)
    request, response = app.test_client.get("/testing.file")
    assert response.status == 404


@pytest.mark.parametrize("use_modified_since", [True, False])
@pytest.mark.parametrize("stream_large_files", [True, 1024])
@pytest.mark.parametrize("file_name", ["test.file", "large.file"])
def test_static_stream_large_file(
    spf,
    static_file_directory,
    file_name,
    use_modified_since,
    stream_large_files,
    large_file,
):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_modified_since=use_modified_since,
        stream_large_files=stream_large_files,
    )
    spf.register_plugin(plugin)
    request, response = app.test_client.get("/testing.file")

    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)


@pytest.mark.parametrize(
    "file_name", ["test.file", "decode me.txt", "python.png"]
)
def test_use_modified_since(spf, static_file_directory, file_name):

    file_stat = os.stat(get_file_path(static_file_directory, file_name))
    modified_since = strftime(
        "%a, %d %b %Y %H:%M:%S GMT", gmtime(file_stat.st_mtime)
    )
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_modified_since=True,
    )
    spf.register_plugin(plugin)
    request, response = app.test_client.get(
        "/testing.file", headers={"If-Modified-Since": modified_since}
    )

    assert response.status == 304


def test_file_not_found(spf, static_file_directory):
    app = spf._app
    plugin = TestPlugin()
    plugin.static("/static", static_file_directory)
    spf.register_plugin(plugin)
    request, response = app.test_client.get("/static/not_found")

    assert response.status == 404
    assert response.text == "Error: File not found"


@pytest.mark.parametrize("static_name", ["_static_name", "static"])
@pytest.mark.parametrize("file_name", ["test.html"])
def test_static_name(spf, static_file_directory, static_name, file_name):
    app = spf._app
    plugin = TestPlugin()
    plugin.static("/static", static_file_directory, name=static_name)
    spf.register_plugin(plugin)
    request, response = app.test_client.get("/static/{}".format(file_name))

    assert response.status == 200


@pytest.mark.parametrize("file_name", ["test.file"])
def test_static_remove_route(spf, static_file_directory, file_name):
    app = spf._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file", get_file_path(static_file_directory, file_name)
    )
    spf.register_plugin(plugin)
    request, response = app.test_client.get("/testing.file")
    assert response.status == 200

    app.remove_route("/testing.file")
    request, response = app.test_client.get("/testing.file")
    assert response.status == 404