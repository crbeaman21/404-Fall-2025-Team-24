import 'dart:async';

import 'package:collection/collection.dart';

import '/backend/schema/util/firestore_util.dart';
import '/backend/schema/util/schema_util.dart';

import 'index.dart';
import '/flutter_flow/flutter_flow_util.dart';

class TesttypesRecord extends FirestoreRecord {
  TesttypesRecord._(
    DocumentReference reference,
    Map<String, dynamic> data,
  ) : super(reference, data) {
    _initializeFields();
  }

  // "one" field.
  bool? _one;
  bool get one => _one ?? false;
  bool hasOne() => _one != null;

  // "two" field.
  bool? _two;
  bool get two => _two ?? false;
  bool hasTwo() => _two != null;

  // "three" field.
  bool? _three;
  bool get three => _three ?? false;
  bool hasThree() => _three != null;

  void _initializeFields() {
    _one = snapshotData['one'] as bool?;
    _two = snapshotData['two'] as bool?;
    _three = snapshotData['three'] as bool?;
  }

  static CollectionReference get collection =>
      FirebaseFirestore.instance.collection('testtypes');

  static Stream<TesttypesRecord> getDocument(DocumentReference ref) =>
      ref.snapshots().map((s) => TesttypesRecord.fromSnapshot(s));

  static Future<TesttypesRecord> getDocumentOnce(DocumentReference ref) =>
      ref.get().then((s) => TesttypesRecord.fromSnapshot(s));

  static TesttypesRecord fromSnapshot(DocumentSnapshot snapshot) =>
      TesttypesRecord._(
        snapshot.reference,
        mapFromFirestore(snapshot.data() as Map<String, dynamic>),
      );

  static TesttypesRecord getDocumentFromData(
    Map<String, dynamic> data,
    DocumentReference reference,
  ) =>
      TesttypesRecord._(reference, mapFromFirestore(data));

  @override
  String toString() =>
      'TesttypesRecord(reference: ${reference.path}, data: $snapshotData)';

  @override
  int get hashCode => reference.path.hashCode;

  @override
  bool operator ==(other) =>
      other is TesttypesRecord &&
      reference.path.hashCode == other.reference.path.hashCode;
}

Map<String, dynamic> createTesttypesRecordData({
  bool? one,
  bool? two,
  bool? three,
}) {
  final firestoreData = mapToFirestore(
    <String, dynamic>{
      'one': one,
      'two': two,
      'three': three,
    }.withoutNulls,
  );

  return firestoreData;
}

class TesttypesRecordDocumentEquality implements Equality<TesttypesRecord> {
  const TesttypesRecordDocumentEquality();

  @override
  bool equals(TesttypesRecord? e1, TesttypesRecord? e2) {
    return e1?.one == e2?.one && e1?.two == e2?.two && e1?.three == e2?.three;
  }

  @override
  int hash(TesttypesRecord? e) =>
      const ListEquality().hash([e?.one, e?.two, e?.three]);

  @override
  bool isValidKey(Object? o) => o is TesttypesRecord;
}
