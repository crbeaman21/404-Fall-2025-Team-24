import 'dart:async';

import 'package:collection/collection.dart';

import '/backend/schema/util/firestore_util.dart';
import '/backend/schema/util/schema_util.dart';

import 'index.dart';
import '/flutter_flow/flutter_flow_util.dart';

class DailydataRecord extends FirestoreRecord {
  DailydataRecord._(
    DocumentReference reference,
    Map<String, dynamic> data,
  ) : super(reference, data) {
    _initializeFields();
  }

  // "date" field.
  String? _date;
  String get date => _date ?? '';
  bool hasDate() => _date != null;

  // "avgCurrent" field.
  double? _avgCurrent;
  double get avgCurrent => _avgCurrent ?? 0.0;
  bool hasAvgCurrent() => _avgCurrent != null;

  // "avgBattery" field.
  double? _avgBattery;
  double get avgBattery => _avgBattery ?? 0.0;
  bool hasAvgBattery() => _avgBattery != null;

  // "avgPower" field.
  double? _avgPower;
  double get avgPower => _avgPower ?? 0.0;
  bool hasAvgPower() => _avgPower != null;

  DocumentReference get parentReference => reference.parent.parent!;

  void _initializeFields() {
    _date = snapshotData['date'] as String?;
    _avgCurrent = castToType<double>(snapshotData['avgCurrent']);
    _avgBattery = castToType<double>(snapshotData['avgBattery']);
    _avgPower = castToType<double>(snapshotData['avgPower']);
  }

  static Query<Map<String, dynamic>> collection([DocumentReference? parent]) =>
      parent != null
          ? parent.collection('dailydata')
          : FirebaseFirestore.instance.collectionGroup('dailydata');

  static DocumentReference createDoc(DocumentReference parent, {String? id}) =>
      parent.collection('dailydata').doc(id);

  static Stream<DailydataRecord> getDocument(DocumentReference ref) =>
      ref.snapshots().map((s) => DailydataRecord.fromSnapshot(s));

  static Future<DailydataRecord> getDocumentOnce(DocumentReference ref) =>
      ref.get().then((s) => DailydataRecord.fromSnapshot(s));

  static DailydataRecord fromSnapshot(DocumentSnapshot snapshot) =>
      DailydataRecord._(
        snapshot.reference,
        mapFromFirestore(snapshot.data() as Map<String, dynamic>),
      );

  static DailydataRecord getDocumentFromData(
    Map<String, dynamic> data,
    DocumentReference reference,
  ) =>
      DailydataRecord._(reference, mapFromFirestore(data));

  @override
  String toString() =>
      'DailydataRecord(reference: ${reference.path}, data: $snapshotData)';

  @override
  int get hashCode => reference.path.hashCode;

  @override
  bool operator ==(other) =>
      other is DailydataRecord &&
      reference.path.hashCode == other.reference.path.hashCode;
}

Map<String, dynamic> createDailydataRecordData({
  String? date,
  double? avgCurrent,
  double? avgBattery,
  double? avgPower,
}) {
  final firestoreData = mapToFirestore(
    <String, dynamic>{
      'date': date,
      'avgCurrent': avgCurrent,
      'avgBattery': avgBattery,
      'avgPower': avgPower,
    }.withoutNulls,
  );

  return firestoreData;
}

class DailydataRecordDocumentEquality implements Equality<DailydataRecord> {
  const DailydataRecordDocumentEquality();

  @override
  bool equals(DailydataRecord? e1, DailydataRecord? e2) {
    return e1?.date == e2?.date &&
        e1?.avgCurrent == e2?.avgCurrent &&
        e1?.avgBattery == e2?.avgBattery &&
        e1?.avgPower == e2?.avgPower;
  }

  @override
  int hash(DailydataRecord? e) => const ListEquality()
      .hash([e?.date, e?.avgCurrent, e?.avgBattery, e?.avgPower]);

  @override
  bool isValidKey(Object? o) => o is DailydataRecord;
}
