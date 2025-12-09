import 'package:flutter/material.dart';
import '/backend/backend.dart';
import '/backend/api_requests/api_manager.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'flutter_flow/flutter_flow_util.dart';

class FFAppState extends ChangeNotifier {
  static FFAppState _instance = FFAppState._internal();

  factory FFAppState() {
    return _instance;
  }

  FFAppState._internal();

  static void reset() {
    _instance = FFAppState._internal();
  }

  Future initializePersistedState() async {}

  void update(VoidCallback callback) {
    callback();
    notifyListeners();
  }

  String _rtdbIdToken = '';
  String get rtdbIdToken => _rtdbIdToken;
  set rtdbIdToken(String value) {
    _rtdbIdToken = value;
  }

  bool _makePhoto = false;
  bool get makePhoto => _makePhoto;
  set makePhoto(bool value) {
    _makePhoto = value;
  }

  String _fileBase64 = '';
  String get fileBase64 => _fileBase64;
  set fileBase64(String value) {
    _fileBase64 = value;
  }

  String _deviceId = 'RnCq5z9aT2PjdWUX2lCQC4XXrTn2';
  String get deviceId => _deviceId;
  set deviceId(String value) {
    _deviceId = value;
  }

  double _batteryVal = 0.0;
  double get batteryVal => _batteryVal;
  set batteryVal(double value) {
    _batteryVal = value;
  }

  double _powerVal = 0.0;
  double get powerVal => _powerVal;
  set powerVal(double value) {
    _powerVal = value;
  }

  double _currentVal = 0.0;
  double get currentVal => _currentVal;
  set currentVal(double value) {
    _currentVal = value;
  }

  double _altitude = 0.0;
  double get altitude => _altitude;
  set altitude(double value) {
    _altitude = value;
  }

  DocumentReference? _currentDeviceRef;
  DocumentReference? get currentDeviceRef => _currentDeviceRef;
  set currentDeviceRef(DocumentReference? value) {
    _currentDeviceRef = value;
  }
}
