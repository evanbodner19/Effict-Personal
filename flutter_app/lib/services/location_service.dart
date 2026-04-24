import 'package:geolocator/geolocator.dart';

class LocationService {
  Position? _cachedPosition;

  Position? get cachedPosition => _cachedPosition;

  Future<Position?> getLocation() async {
    if (_cachedPosition != null) return _cachedPosition;

    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) return null;

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) return null;
      }
      if (permission == LocationPermission.deniedForever) return null;

      _cachedPosition = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.low,
        timeLimit: const Duration(seconds: 5),
      );
      return _cachedPosition;
    } catch (_) {
      return null;
    }
  }
}
