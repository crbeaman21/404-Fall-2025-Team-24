import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

Future initFirebase() async {
  if (kIsWeb) {
    await Firebase.initializeApp(
        options: FirebaseOptions(
            apiKey: "AIzaSyC0n6ZSSnoXQ9d2Pdc-KF2dU3WIf5KCaSM",
            authDomain: "elevate-2-0-07zs58.firebaseapp.com",
            projectId: "elevate-2-0-07zs58",
            storageBucket: "elevate-2-0-07zs58.firebasestorage.app",
            messagingSenderId: "661973341050",
            appId: "1:661973341050:web:90fcd11df116328eb47cc3"));
  } else {
    await Firebase.initializeApp();
  }
}
