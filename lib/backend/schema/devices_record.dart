import 'dart:async';

import 'package:collection/collection.dart';

import '/backend/schema/util/firestore_util.dart';
import '/backend/schema/util/schema_util.dart';

import 'index.dart';
import '/flutter_flow/flutter_flow_util.dart';

/// Jetson Nano connection
class DevicesRecord extends FirestoreRecord {
  DevicesRecord._(
    DocumentReference reference,
    Map<String, dynamic> data,
  ) : super(reference, data) {
    _initializeFields();
  }

  // "allowedUsers" field.
  List<String>? _allowedUsers;
  List<String> get allowedUsers => _allowedUsers ?? const [];
  bool hasAllowedUsers() => _allowedUsers != null;

  // "lastSeen" field.
  DateTime? _lastSeen;
  DateTime? get lastSeen => _lastSeen;
  bool hasLastSeen() => _lastSeen != null;

  // "deviceId" field.
  String? _deviceId;
  String get deviceId => _deviceId ?? '';
  bool hasDeviceId() => _deviceId != null;

  // "battery" field.
  double? _battery;
  double get battery => _battery ?? 0.0;
  bool hasBattery() => _battery != null;

  // "current" field.
  double? _current;
  double get current => _current ?? 0.0;
  bool hasCurrent() => _current != null;

  // "status" field.
  String? _status;
  String get status => _status ?? '';
  bool hasStatus() => _status != null;

  // "voltage" field.
  double? _voltage;
  double get voltage => _voltage ?? 0.0;
  bool hasVoltage() => _voltage != null;

  // "power" field.
  double? _power;
  double get power => _power ?? 0.0;
  bool hasPower() => _power != null;

  // "mode" field.
  String? _mode;
  String get mode => _mode ?? '';
  bool hasMode() => _mode != null;

  // "altitude" field.
  double? _altitude;
  double get altitude => _altitude ?? 0.0;
  bool hasAltitude() => _altitude != null;

  void _initializeFields() {
    _allowedUsers = getDataList(snapshotData['allowedUsers']);
    _lastSeen = snapshotData['lastSeen'] as DateTime?;
    _deviceId = snapshotData['deviceId'] as String?;
    _battery = castToType<double>(snapshotData['battery']);
    _current = castToType<double>(snapshotData['current']);
    _status = snapshotData['status'] as String?;
    _voltage = castToType<double>(snapshotData['voltage']);
    _power = castToType<double>(snapshotData['power']);
    _mode = snapshotData['mode'] as String?;
    _altitude = castToType<double>(snapshotData['altitude']);
  }

  static CollectionReference get collection =>
      FirebaseFirestore.instance.collection('devices');

  static Stream<DevicesRecord> getDocument(DocumentReference ref) =>
      ref.snapshots().map((s) => DevicesRecord.fromSnapshot(s));

  static Future<DevicesRecord> getDocumentOnce(DocumentReference ref) =>
      ref.get().then((s) => DevicesRecord.fromSnapshot(s));

  static DevicesRecord fromSnapshot(DocumentSnapshot snapshot) =>
      DevicesRecord._(
        snapshot.reference,
        mapFromFirestore(snapshot.data() as Map<String, dynamic>),
      );

  static DevicesRecord getDocumentFromData(
    Map<String, dynamic> data,
    DocumentReference reference,
  ) =>
      DevicesRecord._(reference, mapFromFirestore(data));

  @override
  String toString() =>
      'DevicesRecord(reference: ${reference.path}, data: $snapshotData)';

  @override
  int get hashCode => reference.path.hashCode;

  @override
  bool operator ==(other) =>
      other is DevicesRecord &&
      reference.path.hashCode == other.reference.path.hashCode;
}

Map<String, dynamic> createDevicesRecordData({
  DateTime? lastSeen,
  String? deviceId,
  double? battery,
  double? current,
  String? status,
  double? voltage,
  double? power,
  String? mode,
  double? altitude,
}) {
  final firestoreData = mapToFirestore(
    <String, dynamic>{
      'lastSeen': lastSeen,
      'deviceId': deviceId,
      'battery': battery,
      'current': current,
      'status': status,
      'voltage': voltage,
      'power': power,
      'mode': mode,
      'altitude': altitude,
    }.withoutNulls,
  );

  return firestoreData;
}

class DevicesRecordDocumentEquality implements Equality<DevicesRecord> {
  const DevicesRecordDocumentEquality();

  @override
  bool equals(DevicesRecord? e1, DevicesRecord? e2) {
    const listEquality = ListEquality();
    return listEquality.equals(e1?.allowedUsers, e2?.allowedUsers) &&
        e1?.lastSeen == e2?.lastSeen &&
        e1?.deviceId == e2?.deviceId &&
        e1?.battery == e2?.battery &&
        e1?.current == e2?.current &&
        e1?.status == e2?.status &&
        e1?.voltage == e2?.voltage &&
        e1?.power == e2?.power &&
        e1?.mode == e2?.mode &&
        e1?.altitude == e2?.altitude;
  }

  @override
  int hash(DevicesRecord? e) => const ListEquality().hash([
        e?.allowedUsers,
        e?.lastSeen,
        e?.deviceId,
        e?.battery,
        e?.current,
        e?.status,
        e?.voltage,
        e?.power,
        e?.mode,
        e?.altitude
      ]);

  @override
  bool isValidKey(Object? o) => o is DevicesRecord;
}
