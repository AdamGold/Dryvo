from server.api.database.models import Place, PlaceType


def test_place_create_or_find(student):
    place = Place.create_or_find(
        "testing", PlaceType.meetup, student)
    assert isinstance(place,
                      Place)
    assert Place.create_or_find(
        "test", PlaceType.dropoff, student
    ) != place
    same_place = Place.create_or_find(
        "testing", PlaceType.meetup, student)
    assert same_place == place
    not_same_place = Place.create_or_find(
        "in test", PlaceType.meetup, student)
    assert not_same_place != place
    assert same_place.times_used == 2
