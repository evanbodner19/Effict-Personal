import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/item.dart';
import '../models/category.dart';
import 'location_service.dart';

const backendUrl = String.fromEnvironment('BACKEND_URL');

class ApiService {
  final LocationService _locationService = LocationService();

  Future<String> _getToken() async {
    final session = Supabase.instance.client.auth.currentSession;
    if (session == null) throw Exception('Not authenticated');
    return session.accessToken;
  }

  Future<Map<String, String>> _headers() async {
    final token = await _getToken();
    return {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    };
  }

  String _locationParams() {
    final pos = _locationService.cachedPosition;
    if (pos == null) return '';
    final tz = DateTime.now().timeZoneName;
    return '?lat=${pos.latitude}&lng=${pos.longitude}&tz=$tz';
  }

  Future<Map<String, dynamic>> syncAll() async {
    await _locationService.getLocation();
    final headers = await _headers();
    final resp = await http.post(
      Uri.parse('$backendUrl/api/sync/all${_locationParams()}'),
      headers: headers,
    );
    return jsonDecode(resp.body);
  }

  Future<List<Item>> getTop() async {
    final headers = await _headers();
    final resp = await http.get(
      Uri.parse('$backendUrl/api/top'),
      headers: headers,
    );
    final list = jsonDecode(resp.body) as List;
    return list.map((j) => Item.fromJson(j)).toList();
  }

  Future<List<Category>> getCategories() async {
    final headers = await _headers();
    final resp = await http.get(
      Uri.parse('$backendUrl/api/categories'),
      headers: headers,
    );
    final list = jsonDecode(resp.body) as List;
    return list.map((j) => Category.fromJson(j)).toList();
  }

  Future<void> completeItem(String itemId) async {
    final headers = await _headers();
    await http.post(
      Uri.parse('$backendUrl/api/items/$itemId/complete'),
      headers: headers,
    );
  }

  Future<void> deferItem(String itemId) async {
    final headers = await _headers();
    await http.post(
      Uri.parse('$backendUrl/api/items/$itemId/defer'),
      headers: headers,
    );
  }

  Future<void> createItem(Map<String, dynamic> data) async {
    final headers = await _headers();
    await http.post(
      Uri.parse('$backendUrl/api/items'),
      headers: headers,
      body: jsonEncode(data),
    );
  }

  Future<void> updateItem(String itemId, Map<String, dynamic> data) async {
    final headers = await _headers();
    await http.patch(
      Uri.parse('$backendUrl/api/items/$itemId'),
      headers: headers,
      body: jsonEncode(data),
    );
  }

  Future<void> deleteItem(String itemId) async {
    final headers = await _headers();
    await http.delete(
      Uri.parse('$backendUrl/api/items/$itemId'),
      headers: headers,
    );
  }

  Future<void> reorderCategories(List<String> order) async {
    final headers = await _headers();
    await http.put(
      Uri.parse('$backendUrl/api/categories/reorder'),
      headers: headers,
      body: jsonEncode({'order': order}),
    );
  }

  Future<void> createCategory(String title, int rank) async {
    final headers = await _headers();
    await http.post(
      Uri.parse('$backendUrl/api/categories'),
      headers: headers,
      body: jsonEncode({'title': title, 'rank': rank}),
    );
  }

  Future<void> deleteCategory(String categoryId) async {
    final headers = await _headers();
    await http.delete(
      Uri.parse('$backendUrl/api/categories/$categoryId'),
      headers: headers,
    );
  }
}
