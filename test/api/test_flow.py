from uuid import uuid4

from tracardi.process_engine.action.v1.flow.start.start_action import StartAction

from tracardi.domain.flow import Flow
from tracardi.process_engine.action.v1.end_action import EndAction
from tracardi.service.wf.service.builders import action

from ..utils import Endpoint

endpoint = Endpoint()


def test_should_return_404_on_get_flow_if_none():
    flow_id = str(uuid4())
    response = endpoint.get(f'/flow/draft/{flow_id}')
    assert response.status_code == 404
    assert response.json() is None


def test_should_return_404_on_delete_flow_if_none():
    flow_id = str(uuid4())
    response = endpoint.delete(f'/flow/{flow_id}')
    assert response.status_code == 404
    assert response.json() is None


def create_flow(id, name, desc):
    data = {
        "id": id,
        "name": name,
        "description": desc,
        "enabled": True,
        "projects": [
            "General", "Test"
        ],
        "draft": "",
        "production": "",
        "lock": False
    }

    return endpoint.post('/flow/metadata', data=data)


def check_flow_bool(id, lock, type='lock', field='lock'):
    on_off = 'yes' if lock else 'no'

    response = endpoint.get(f'/flow/{id}/{type}/{on_off}')
    assert response.status_code == 200
    result = response.json()
    assert result == {'saved': 1, 'errors': [], 'ids': [id]}

    # flush data to elastic
    assert endpoint.get('/flows/refresh').status_code == 200

    # read flow
    response = endpoint.get(f'/flow/metadata/{id}')
    assert response.status_code == 200
    if response.status_code == 200:
        result = response.json()
        assert result[field] is lock
    else:
        raise Exception("Could not read flow id {}".format(id))


def test_should_load_flows():
    result = endpoint.get('/flows')
    result = result.json()
    assert 'total' in result
    assert 'result' in result


def test_should_create_flow():
    id = str(uuid4())

    try:
        # delete flow
        assert endpoint.delete(f'/flow/{id}').status_code in [200, 404]

        # add flow

        response = create_flow(id, "Test flow", "Opis")
        assert {'saved': 1, 'errors': [], 'ids': [id]} == response.json()

        # flush data to elastic
        assert endpoint.get('/flows/refresh').status_code == 200

        # read saved flow

        response = endpoint.get(f'/flow/metadata/{id}')
        assert response.status_code == 200
        if response.status_code == 200:
            result = response.json()
            assert result['id'] == id
            assert result['name'] == 'Test flow'

            # delete flow
            assert endpoint.delete(f'/flow/{id}').status_code == 200

            # flush data to elastic
            assert endpoint.get('/flows/refresh').status_code == 200

            # response = endpoint.get(f'/flow/metadata/{id}')
            # print(response.content)
            # check if do not exist
            assert endpoint.get(f'/flow/metadata/{id}').status_code == 404

    finally:
        assert endpoint.delete(f'/flow/{id}').status_code in [200, 404]
        assert endpoint.get('/flows/refresh').status_code == 200


def test_get_flow_ok():
    id = str(uuid4())

    # delete flow
    assert endpoint.delete(f'/flow/{id}').status_code in [200, 404]

    # flush data to elastic
    assert endpoint.get('/flows/refresh').status_code == 200

    # check if do not exist
    assert endpoint.get(f'/flow/draft/{id}').status_code == 404
    assert endpoint.get(f'/flow/production/{id}').status_code == 404


def test_should_update_flow_metadata():
    id = str(uuid4())

    try:
        # delete flow
        assert endpoint.delete(f'/flow/{id}').status_code in [200, 404]

        # flush data to elastic
        assert endpoint.get('/flows/refresh').status_code == 200

        # create flow
        response = create_flow(id, "Test flow", "Opis")
        assert response.status_code == 200
        result = response.json()
        assert result == {'saved': 1, 'errors': [], 'ids': [id]}

        # flush data to elastic
        assert endpoint.get('/flows/refresh').status_code == 200

        response = endpoint.get(f'/flow/production/{id}')
        assert response.status_code == 200
        if response.status_code == 200:
            result = response.json()
            assert result['id'] == id
            assert result['name'] == 'Test flow'
        else:
            raise Exception("Could not read flow")

        response = endpoint.get(f'/flow/draft/{id}')
        assert response.status_code == 200
        if response.status_code == 200:
            result = response.json()
            assert result['id'] == id
            assert result['name'] == 'Test flow'
        else:
            raise Exception("Could not read flow")

        response = endpoint.post('/flow/metadata', data={
            "id": id,
            "name": "New name",
            "description": "New Description",
            "enabled": False,
            "projects": [
                "New"
            ]
        })

        result = response.json()
        assert response.status_code == 200
        assert result == {'saved': 1, 'errors': [], 'ids': [id]}

        # flush data to elastic
        assert endpoint.get('/flows/refresh').status_code == 200

        # get updated flow

        response = endpoint.get(f'/flow/metadata/{id}')
        assert response.status_code == 200
        if response.status_code == 200:
            result = response.json()
            assert result['id'] == id
            assert result['name'] == 'New name'
            assert result['description'] == 'New Description'
            assert "New" in result['projects']
        else:
            raise Exception("Could not read flow")

    finally:
        assert endpoint.delete(f'/flow/{id}').status_code in [200, 404]


def test_should_enable_flow_lock():
    id = str(uuid4())

    try:
        assert endpoint.delete(f'/flow/{id}').status_code == 404

        # create flow
        response = create_flow(id, "Test flow", "Opis")
        assert response.status_code == 200

        # read flow
        check_flow_bool(id, True, type='lock', field='lock')
        check_flow_bool(id, False, type='lock', field='lock')

    finally:
        assert endpoint.delete(f'/flow/{id}').status_code in [200, 404]


# todo flow delete deletes also rules.


def test_flow_code_api():
    id = str(uuid4())

    try:

        # Add event

        start = action(StartAction)
        end = action(EndAction)

        flow = Flow.build("Test wf as a code", id=id)
        flow += start('payload') >> end('payload')

        response = endpoint.post('/flow/draft', data=flow.dict())
        assert response.status_code == 200
        result = response.json()
        assert result['saved'] == 1
        assert id in result['ids']

    finally:
        assert endpoint.delete(f'/flow/{id}').status_code in [200, 404]


def test_should_save_draft_metadata():
    try:
        flow_id = str(uuid4())
        response = create_flow(flow_id, "Test flow", "Opis")
        assert response.status_code == 200

        payload = {
            "id": flow_id,
            "name": "string",
            "description": "string",
            "enabled": True,
            "projects": [
                "General"
            ]
        }
        assert endpoint.post(f'/flow/draft/metadata', data=payload).status_code == 200
        assert endpoint.get(f'/flows/refresh').status_code == 200

        response = endpoint.get(f'/flow/draft/{flow_id}')
        assert response.status_code == 200
        result = response.json()
        assert result['name'] == payload['name']
    finally:
        assert endpoint.delete(f'/flow/{flow_id}').status_code in [200, 404]