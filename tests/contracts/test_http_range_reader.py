"""Bounded importer HTTP consumers using fake connections only, never network."""
from collections import deque
import importlib.util
import http.client
import io
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('http_range_under_test', ROOT/'scripts/prepare_jezero_terrain.py')
terrain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terrain)
URL = 'https://example.invalid/source.tif'


class Response:
    def __init__(self, body=b'cdef', status=206, headers=None, forbid_read=False):
        self.status = status
        self.headers = {'Content-Range': 'bytes 2-5/10', 'Content-Length': '4'} if headers is None else headers
        self.body, self.forbid_read = body, forbid_read
        self.reads = []

    def getheaders(self):
        return list(self.headers.items())

    def read(self, size=None):
        assert not self.forbid_read, 'invalid response body must not be read at all'
        assert type(size) is int and size >= 0, 'unbounded read is forbidden'
        self.reads.append(size)
        return self.body[:size]


@pytest.fixture
def wire(monkeypatch):
    pending, connections = deque(), []
    terrain._TLS_LOCAL.conns = {}
    terrain._BLOCK_CACHE.clear()
    terrain._resolve_upstream_cached.cache_clear()

    class Connection:
        def __init__(self, host, timeout):
            self.host, self.timeout = host, timeout
            self.closed = False
            self.requests = []
            connections.append(self)

        def request(self, method, path, headers):
            self.requests.append((method, path, headers))

        def getresponse(self):
            assert pending, 'unexpected request would have required network'
            result = pending.popleft()
            if isinstance(result, Exception):
                raise result
            return result

        def close(self):
            self.closed = True

    monkeypatch.setattr(terrain.http.client, 'HTTPSConnection', Connection)
    yield pending, connections
    for host in list(getattr(terrain._TLS_LOCAL, 'conns', {})):
        terrain._drop_https_conn(host)
    terrain._BLOCK_CACHE.clear()
    terrain._resolve_upstream_cached.cache_clear()


def fetch(**changes):
    return terrain._request_with_keepalive('GET', URL, {'Range': 'bytes=2-5'}, expected_total=10, **changes)


def test_valid_range_is_read_once_with_one_byte_bound_and_keepalive_reused(wire):
    pending, connections = wire
    first = Response()
    second = Response(b'ghij', headers={'content-range': 'bytes 6-9/10', 'content-length': '4'})
    pending.extend([first, second])
    assert fetch()[2] == b'cdef'
    assert terrain._request_with_keepalive('GET', URL+'?version=1', {'range': 'bytes=6-9'}, expected_total=10)[2] == b'ghij'
    assert first.reads == second.reads == [5]
    assert len(connections) == 1 and not connections[0].closed
    assert connections[0].requests[1][1] == '/source.tif?version=1'
    assert all(h['Connection'] == 'keep-alive' for _, _, h in connections[0].requests)


@pytest.mark.parametrize('status,headers', [
    (200, {'Content-Length': '5000000000'}),
    (404, {'Content-Length': '12'}),
    (206, {'Content-Range': 'bytes 0-3/10', 'Content-Length': '4'}),
    (206, {'Content-Range': 'bytes 2-6/10', 'Content-Length': '4'}),
    (206, {'Content-Range': 'bytes 2-5/20', 'Content-Length': '4'}),
    (206, {'Content-Range': 'bytes 2-5/5', 'Content-Length': '4'}),
    (206, {'Content-Range': 'bytes 2-5/*', 'Content-Length': '4'}),
    (206, {'Content-Range': 'bytes */10', 'Content-Length': '4'}),
    (206, {'Content-Length': '4'}),
    (206, {'Content-Range': 'bytes 2-5/10', 'Content-Length': '5000000000'}),
    (206, {'Content-Range': 'bytes 2-5/10', 'Content-Length': '3'}),
    (206, {'Content-Range': 'bytes 2-5/10', 'Content-Length': '-4'}),
    (206, {'Content-Range': 'bytes 2-5/10'}),
    (206, {'Content-Range': 'bytes 2-5/10', 'Content-Length': '4', 'Content-Encoding': 'gzip'}),
    (206, {'Content-Range': 'bytes 2-5/10', 'Content-Length': '4', 'Transfer-Encoding': 'chunked'}),
])
def test_invalid_status_or_headers_drop_connection_before_any_body_read(wire, status, headers):
    pending, connections = wire
    response = Response(status=status, headers=headers, forbid_read=True)
    pending.append(response)
    with pytest.raises(OSError):
        fetch()
    assert response.reads == []
    assert len(connections) == 1 and connections[0].closed
    assert not terrain._TLS_LOCAL.conns


@pytest.mark.parametrize('body', [b'abc', b'abcde', b'x'*65536], ids=['truncated', 'one-extra', 'large-body'])
def test_truncated_or_oversized_body_is_bounded_and_never_cached(wire, body):
    pending, connections = wire
    response = Response(body=body)
    pending.append(response)
    with pytest.raises(OSError, match='body has'):
        fetch()
    assert response.reads == [5] and connections[0].closed
    assert terrain._BLOCK_CACHE == {}


def test_single_block_and_final_short_block_are_validated_before_cache(wire):
    pending, connections = wire
    first = Response(b'abcd', headers={'Content-Range': 'bytes 0-3/10', 'Content-Length': '4'})
    last = Response(b'ij', headers={'Content-Range': 'bytes 8-9/10', 'Content-Length': '2'})
    pending.extend([first, last])
    assert terrain._fetch_shared_block(URL, 'etag-1', 10, 4, 0) == b'abcd'
    assert terrain._fetch_shared_block(URL, 'etag-1', 10, 4, 2) == b'ij'
    assert terrain._fetch_shared_block(URL, 'etag-1', 10, 4, 0) == b'abcd'  # No second request.
    assert first.reads == [5] and last.reads == [3]
    assert len(connections[0].requests) == 2
    assert connections[0].requests[0][2]['If-Match'] == 'etag-1'
    assert connections[0].requests[0][2]['Accept-Encoding'] == 'identity'


def test_coalesced_range_splits_only_validated_bytes_and_reader_reuses_cache(wire):
    pending, connections = wire
    response = Response(b'abcdefghij', headers={'Content-Range': 'bytes 0-9/10', 'Content-Length': '10'})
    pending.append(response)
    terrain._prefetch_contiguous_blocks(URL, 'etag-1', 10, 4, 0, 2)
    assert response.reads == [11]
    assert connections[0].requests[0][2]['Range'] == 'bytes=0-9'
    assert [terrain._BLOCK_CACHE[(URL, 'etag-1', 4, index)] for index in range(3)] == [b'abcd', b'efgh', b'ij']
    reader = terrain.HTTPRangeReader(URL, {'Content-Length': '10', 'ETag': 'etag-1'}, block_size=4)
    reader.seek(1)
    assert reader.read(7) == b'bcdefgh'
    assert reader.tell() == 8
    assert reader.read() == b'ij' and reader.read(1) == b''
    assert len(connections[0].requests) == 1


def test_invalid_coalesced_range_cannot_fill_any_cache_entry(wire):
    pending, connections = wire
    response = Response(headers={'Content-Range': 'bytes 0-9/10', 'Content-Length': '999999'}, forbid_read=True)
    pending.append(response)
    with pytest.raises(OSError, match='Content-Length'):
        terrain._prefetch_contiguous_blocks(URL, None, 10, 4, 0, 2)
    assert response.reads == [] and connections[0].closed
    assert terrain._BLOCK_CACHE == {}


def test_oversized_single_block_body_is_not_cached(wire):
    pending, connections = wire
    response = Response(b'abcde', headers={'Content-Range': 'bytes 0-3/10', 'Content-Length': '4'})
    pending.append(response)
    with pytest.raises(OSError, match='body has'):
        terrain._fetch_shared_block(URL, None, 10, 4, 0)
    assert response.reads == [5] and connections[0].closed
    assert terrain._BLOCK_CACHE == {}


def test_conflicting_framing_headers_are_rejected_before_body_read(wire):
    pending, connections = wire
    response = Response(headers={'Content-Range': 'bytes 2-5/10', 'Content-Length': '5000000000',
                                 'content-length': '4'}, forbid_read=True)
    pending.append(response)
    with pytest.raises(OSError, match='conflicting upstream'):
        fetch()
    assert response.reads == [] and connections[0].closed


@pytest.mark.parametrize('method', ['HEAD', 'GET'])
def test_stdlib_http_response_finishes_valid_framing_without_read_to_eof(wire, method):
    pending, connections = wire
    raw = (b'HTTP/1.1 206 Partial Content\r\nContent-Range: bytes 2-5/10\r\n'
           b'Content-Length: 4\r\nConnection: keep-alive\r\n\r\ncdef')
    stream = io.BytesIO(raw)
    class Socket:
        def makefile(self, *args):
            return stream
    response = http.client.HTTPResponse(Socket(), method=method)
    response.begin()
    original_read, reads = response.read, []
    def observed_read(size=None):
        reads.append(size)
        return original_read(size)
    response.read = observed_read
    pending.append(response)
    _, _, body = terrain._request_with_keepalive(method, URL,
        {} if method == 'HEAD' else {'Range': 'bytes=2-5'}, expected_total=10)
    assert body == (b'' if method == 'HEAD' else b'cdef')
    assert reads == ([0] if method == 'HEAD' else [5])
    assert response.isclosed() and not connections[0].closed


def test_transport_failure_retries_with_a_new_connection_and_preserves_valid_keepalive(wire):
    pending, connections = wire
    response = Response()
    pending.extend([ConnectionResetError('stale keepalive'), response])
    assert fetch()[2] == b'cdef'
    assert len(connections) == 2 and connections[0].closed and not connections[1].closed
    assert response.reads == [5]


def test_head_never_drains_resource_body_and_upstream_fallback_still_works(wire):
    pending, connections = wire
    missing = Response(status=404, headers={'Content-Length': '5000000000'})
    available = Response(status=200, headers={'Content-Length': '10', 'ETag': 'etag-1'})
    pending.extend([missing, available])
    result = terrain.resolve_upstream({'source_url': URL,
        'fallback_urls': ['https://fallback.invalid/source.tif'], 'instrument': 'test'})
    assert result == ('https://fallback.invalid/source.tif', {'Content-Length': '10', 'ETag': 'etag-1'})
    assert missing.reads == available.reads == [0]
    assert len(connections) == 2
    assert terrain.resolve_upstream({'source_url': URL,
        'fallback_urls': ['https://fallback.invalid/source.tif'], 'instrument': 'test'}) == result
    assert all(len(conn.requests) == 1 for conn in connections)  # Resolution cache is preserved.


@pytest.mark.parametrize('range_header', ['', 'bytes=2-', 'bytes=-10', 'bytes=5-2', 'bytes=0-1,4-5'])
def test_unbounded_or_multipart_request_is_rejected_before_connection(wire, range_header):
    _, connections = wire
    with pytest.raises(ValueError, match='bounded byte range'):
        terrain._request_with_keepalive('GET', URL, {'Range': range_header})
    assert connections == []
