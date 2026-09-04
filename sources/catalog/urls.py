from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("catalog/", views.attraction_list, name="attraction_list"),
    path("catalog/<slug:slug>/", views.attraction_detail, name="attraction_detail"),
    path("map/", views.map_page, name="map"),
    path("events/", views.event_list, name="event_list"),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path("routes/", views.route_list, name="route_list"),
    path("routes/<slug:slug>/", views.route_detail, name="route_detail"),
    path("villages/<slug:slug>/", views.village_detail, name="village_detail"),
    path("api/attractions.json", views.attractions_geojson, name="attractions_json"),
    path("favorite/<slug:slug>/toggle/", views.toggle_favorite, name="toggle_favorite"),
    path("about/", views.about, name="about"),
    path("how-to-get/", views.how_to_get, name="how_to_get"),
    path("contacts/", views.contacts, name="contacts"),
]
