import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/student_model.dart';
import '../services/api_service.dart';

class AuthProvider extends ChangeNotifier {
  StudentProfile? _student;
  bool _isLoading = false;
  bool _isWarmingUp = false;
  String? _error;

  StudentProfile? get student => _student;
  bool get isLoading => _isLoading;
  bool get isWarmingUp => _isWarmingUp;
  bool get isAuthenticated => _student != null;
  String? get error => _error;

  // Fire-and-forget health ping so Cloud Run isn't cold when user hits Login
  Future<void> warmUp() async {
    _isWarmingUp = true;
    notifyListeners();
    try {
      await ApiService().healthCheck().timeout(const Duration(seconds: 20));
    } catch (_) {} finally {
      _isWarmingUp = false;
      notifyListeners();
    }
  }

  Future<void> loadSavedSession() async {
    final prefs = await SharedPreferences.getInstance();
    final studentJson = prefs.getString('student_profile');
    final token = prefs.getString('auth_token');
    if (token != null) ApiService().setToken(token);
    if (studentJson != null) {
      _student = StudentProfile.fromJson(jsonDecode(studentJson) as Map<String, dynamic>);
      notifyListeners();
    }
  }

  Future<void> login(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final data = await ApiService().login(username, password);
      final token = data['access_token'] as String?;
      if (token != null) ApiService().setToken(token);
      _student = StudentProfile.fromJson(data);
      await _saveSession(token: token);
    } catch (e) {
      _error = e.toString().replaceFirst('ApiException(401): ', '').replaceFirst('ApiException(400): ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> register({
    required String username,
    required String email,
    required String password,
    required String confirmPassword,
    required String fullName,
    required String examTarget,
    String language = 'en',
    String trade = '',
    String engineeringDiscipline = '',
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final data = await ApiService().register(
        username: username,
        email: email,
        password: password,
        confirmPassword: confirmPassword,
        fullName: fullName,
        examTarget: examTarget,
        language: language,
        trade: trade,
        engineeringDiscipline: engineeringDiscipline,
      );
      final token = data['access_token'] as String?;
      if (token != null) ApiService().setToken(token);
      _student = StudentProfile.fromJson(data);
      await _saveSession(token: token);
    } catch (e) {
      _error = e.toString().replaceFirst('ApiException(409): ', '').replaceFirst('ApiException(400): ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> demoLogin(String exam, String language, {String name = 'Demo Student'}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final data = await ApiService().demoLogin(exam, language, name: name);
      final token = data['access_token'] as String?;
      if (token != null) ApiService().setToken(token);
      _student = StudentProfile.fromJson(data);
      await _saveSession(token: token);
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refreshStudent() async {
    if (_student == null) return;
    try {
      final data = await ApiService().getStudent(_student!.studentId);
      _student = StudentProfile.fromJson(data);
      await _saveSession();
      notifyListeners();
    } catch (_) {}
  }

  void updateStudent(StudentProfile updated) {
    _student = updated;
    _saveSession();
    notifyListeners();
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('student_profile');
    await prefs.remove('auth_token');
    ApiService().clearToken();
    _student = null;
    _error = null;
    notifyListeners();
  }

  Future<void> _saveSession({String? token}) async {
    if (_student == null) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('student_profile', jsonEncode(_student!.toJson()));
    if (token != null) await prefs.setString('auth_token', token);
  }
}
