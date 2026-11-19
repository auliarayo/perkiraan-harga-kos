from django.urls import path
import views

app_name = "prediksi"

urlpatterns = [
    path("", views.index, name="index"),
]