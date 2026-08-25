<?php
  $page = "windev";
  $convertUrl = "https://windevconvertor.me/";
  $onSite = file_exists(__DIR__ . "/assets/css/style.css");
  $logoWinDev = "images/logoWinDev.png";
  foreach (array("png", "webp", "jpg", "jpeg", "svg") as $ext) {
    $candidate = "images/logoWinDev." . $ext;
    if (file_exists(__DIR__ . "/" . $candidate)) {
      $logoWinDev = $candidate;
      break;
    }
  }
  $favicon = file_exists(__DIR__ . "/images/program-devize.ico") ? "/images/program-devize.ico" : "logo.ico";
  if (file_exists(__DIR__ . "/php/connect.php")) {
    include_once "php/connect.php";
    include_once "php/config.php";
    include_once "php/functions.php";
  }
?>
<!DOCTYPE html>
<html lang="ro">

<head>
  <meta charset="utf-8">
  <meta content="width=device-width, initial-scale=1.0" name="viewport">

  <?php
    if (file_exists(__DIR__ . "/php/content_head.php")) {
      include_once "php/content_head.php";
    } else {
      echo "<title>WinDev — Convertor Winsmeta → Deviz360 | Softconstruct</title>";
    }
  ?>

  <link href="<?php echo htmlspecialchars($favicon); ?>" rel="icon">
  <link href="<?php echo htmlspecialchars($favicon); ?>" rel="apple-touch-icon">

  <?php if ($onSite) { ?>
  <link href="assets/vendor/bootstrap/css/bootstrap.min.css" rel="stylesheet">
  <link href="assets/vendor/bootstrap-icons/bootstrap-icons.css" rel="stylesheet">
  <link href="assets/vendor/boxicons/css/boxicons.min.css" rel="stylesheet">
  <link href="assets/css/style.css" rel="stylesheet">
  <?php } else { ?>
  <link href="https://fonts.googleapis.com/css2?family=Jost:wght@400;500;600;700&family=Open+Sans:wght@400;600&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css" rel="stylesheet">
  <link href="web/static/css/prezentare.css" rel="stylesheet">
  <?php } ?>

  <style type="text/css">
    .a{
      width: 300px;
      height: auto;
      margin: 10px;
    }
    .b{
      display: flex;
      justify-content: center;
      align-items: stretch;
      text-align: center;
    }
  </style>
</head>

<body>

  <header id="header" class="fixed-top ">
    <?php
      if (file_exists(__DIR__ . "/navbar.php")) {
        include_once "navbar.php";
      } else {
    ?>
    <div class="container d-flex align-items-center">
      <h1 class="logo me-auto"><a href="windev.php">WinDev</a></h1>
      <nav id="navbar" class="navbar">
        <ul>
          <li><a class="nav-link scrollto active" href="#hero">Acasă</a></li>
          <li><a class="nav-link scrollto" href="#pricing">Despre</a></li>
          <li><a class="nav-link scrollto" href="#services">Cum lucrează</a></li>
          <li><a class="nav-link scrollto" href="#why-us">Pași</a></li>
          <li><a class="getstarted scrollto" href="<?php echo htmlspecialchars($convertUrl); ?>">Accesează WinDev</a></li>
        </ul>
      </nav>
    </div>
    <?php } ?>
  </header>

  <section id="hero" class="d-flex align-items-center">
    <div class="container">
      <div class="row">
        <div class="col-lg-6 d-flex flex-column justify-content-center pt-4 pt-lg-0 order-2 order-lg-1">
          <h1>WinDev</h1>
          <h2>Convertor online Winsmeta → Deviz360. Programul este în curs de elaborare; aceasta nu este varianta finală.</h2>
          <div class="d-flex">
            <a href="<?php echo htmlspecialchars($convertUrl); ?>" class="btn-get-started scrollto">Accesează WinDev</a>
          </div>
        </div>
        <div class="col-lg-6 order-1 order-lg-2 hero-img text-center">
          <img src="<?php echo htmlspecialchars($logoWinDev); ?>" class="img-fluid" alt="WinDev" style="max-height: 320px;">
        </div>
      </div>
    </div>
  </section>

  <section id="pricing" class="pricing">
    <div class="container">
      <div class="section-title">
        <h2>WinDev</h2>
        <p style="padding-top: 20px;">Aveți proiecte Winsmeta și lucrați în Deviz360?</p>
      </div>
      <div class="row">
        <div class="col-lg-4">
          <div class="box">
            <h3>Ce este WinDev</h3>
            <ul class="show-glossary">
              <li><i class="bx bx-check"></i>Convertor online realizat de Softconstruct pentru trecerea proiectelor Winsmeta (.KOS) în format Deviz360 (.xlsx).</li>
              <li><i class="bx bx-check"></i>Nu înlocuiește Deviz360: pregătește fișierul pe care îl importați apoi în program.</li>
              <li><i class="bx bx-check"></i><strong>Aceasta este o variantă de test</strong>, în curs de elaborare, nu varianta finală.</li>
            </ul>
          </div>
        </div>
        <div class="col-lg-4 mt-4 mt-lg-0">
          <div class="box">
            <h3>Cum lucrează</h3>
            <ul class="show-glossary">
              <li><i class="bx bx-check"></i>Încărcați arhiva ZIP a folderului proiectului Winsmeta (ex: CS1.KOS), cu fișierele POZYCJE.DB, NAKLADY.DB, INDEKS.DB.</li>
              <li><i class="bx bx-check"></i>WinDev citește tabelele Paradox, recunoaște denumirile, resursele, cantitățile și recapitulările disponibile.</li>
              <li><i class="bx bx-check"></i>Generează și descarcă automat un fișier Excel (.xlsx) pregătit pentru Deviz360, cu devize separate (construcție, montare, utilaj) când există în proiect.</li>
            </ul>
          </div>
        </div>
        <div class="col-lg-4 mt-4 mt-lg-0">
          <div class="box">
            <h3>După conversie</h3>
            <ul class="show-glossary">
              <li><i class="bx bx-check"></i>Importați fișierul în Deviz360 prin <strong>Import → Devize și echipamente</strong>.</li>
              <li><i class="bx bx-check"></i>Configurați recapitulația la fiecare deviz. În unele versiuni Winsmeta ea lipsește — verificați și introduceți recapitulațiile.</li>
              <li><i class="bx bx-check"></i>Prețul final poate să difere cu 0–0,99%, deoarece Deviz360 calculează cu multe cifre după virgulă, spre deosebire de Winsmeta.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="services" class="services section-bg">
    <div class="container">
      <div class="section-title">
        <h2>Cum lucrează</h2>
        <p>Trei pași, de la arhiva Winsmeta până în Deviz360</p>
      </div>
      <div class="row b">
        <div class="a">
          <div class="icon-box a">
            <div class="icon"><i class="bx bx-archive"></i></div>
            <h4><a href="<?php echo htmlspecialchars($convertUrl); ?>">Pregătiți arhiva</a></h4>
            <span class="show-glossary">
              <p>Găsiți folderul proiectului Winsmeta (ex: CS1.KOS), comprimați-l ZIP și încărcați-l în WinDev. Pe serverul online folosiți ZIP, nu RAR.</p>
            </span>
          </div>
        </div>
        <div class="a">
          <div class="icon-box a">
            <div class="icon"><i class="bx bx-transfer"></i></div>
            <h4><a href="<?php echo htmlspecialchars($convertUrl); ?>">Conversie automată</a></h4>
            <span class="show-glossary">
              <p>WinDev citește datele de proiect, norme, resurse și valori, apoi descarcă fișierul .xlsx gata de import.</p>
            </span>
          </div>
        </div>
        <div class="a">
          <div class="icon-box a">
            <div class="icon"><i class="bx bx-import"></i></div>
            <h4><a href="<?php echo htmlspecialchars($convertUrl); ?>">Import în Deviz360</a></h4>
            <span class="show-glossary">
              <p>Deschideți Deviz360 și folosiți Import → Devize și echipamente, apoi verificați recapitulațiile fiecărui deviz.</p>
            </span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="why-us" class="why-us section-bg">
    <div class="section-title">
      <h2>Pași de utilizare</h2>
      <p>Accesați convertorul de test și urmați pașii de mai jos.</p>
    </div>
    <div class="container-fluid show-glossary">
      <div class="row">
        <div class="col-lg-7 d-flex flex-column justify-content-center align-items-stretch order-2 order-lg-1">
          <div class="content" id="WinDev">
            <p>
              WinDev se folosește din browser, fără instalare. Încărcați arhiva proiectului Winsmeta, așteptați conversia și descărcați Excel-ul pentru Deviz360.
              <strong>Varianta actuală este de test</strong> și nu este varianta finală.
            </p>
          </div>
          <div class="accordion-list">
            <ul>
              <li>
                <a data-bs-toggle="collapse" class="collapsed" data-bs-target="#accordion-windev-1"><span>01</span> ACCESAȚI <i class="bx bx-chevron-down icon-show"></i><i class="bx bx-chevron-up icon-close"></i></a>
                <div id="accordion-windev-1" class="collapse show" data-bs-parent=".accordion-list">
                  <p><a href="<?php echo htmlspecialchars($convertUrl); ?>" target="_blank">Apăsați aici</a> pentru a deschide convertorul online WinDev (varianta de test).</p>
                </div>
              </li>
              <li>
                <a data-bs-toggle="collapse" data-bs-target="#accordion-windev-2" class="collapsed"><span>02</span> ÎNCĂRCAȚI ZIP<i class="bx bx-chevron-down icon-show"></i><i class="bx bx-chevron-up icon-close"></i></a>
                <div id="accordion-windev-2" class="collapse" data-bs-parent=".accordion-list">
                  <p>Selectați arhiva ZIP a folderului .KOS. În arhivă trebuie să fie fișierele Paradox ale proiectului Winsmeta.</p>
                </div>
              </li>
              <li>
                <a data-bs-toggle="collapse" data-bs-target="#accordion-windev-3" class="collapsed"><span>03</span> CONVERTIȚI<i class="bx bx-chevron-down icon-show"></i><i class="bx bx-chevron-up icon-close"></i></a>
                <div id="accordion-windev-3" class="collapse" data-bs-parent=".accordion-list">
                  <p>Apăsați „Convertește în Deviz360”. Fișierul .xlsx se descarcă automat, apoi apare un mesaj cu instrucțiunile de import.</p>
                </div>
              </li>
              <li>
                <a data-bs-toggle="collapse" data-bs-target="#accordion-windev-4" class="collapsed"><span>04</span> IMPORTAȚI ÎN DEVIZ360<i class="bx bx-chevron-down icon-show"></i><i class="bx bx-chevron-up icon-close"></i></a>
                <div id="accordion-windev-4" class="collapse" data-bs-parent=".accordion-list">
                  <p>În Deviz360 folosiți Import → Devize și echipamente, apoi configurați recapitulația la fiecare deviz.</p>
                </div>
              </li>
            </ul>
          </div>
        </div>
        <div class="col-lg-5 d-flex flex-column justify-content-center align-items-stretch order-1 order-lg-2" style="padding: 40px;">
          <div class="content">
            <h3>Reclamații și feedback</h3>
            <p>
              Dacă aveți reclamații, observații sau feedback despre WinDev, reveniți la
              <strong>reprezentanții companiei Softconstruct</strong>.
            </p>
            <p>Suport tehnic: <strong>060 830 065</strong></p>
            <p>Aceasta este o <strong>variantă de test</strong>, nu produsul final.</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <footer id="footer">
    <?php
      if (file_exists(__DIR__ . "/footer.php")) {
        $parentPage = "windev";
        include_once "footer.php";
      } else {
        echo '<div class="container"><div class="copyright">Softconstruct 2026 · WinDev · convertor de test</div></div>';
      }
    ?>
  </footer>

  <div id="preloader"></div>
  <a href="#" class="back-to-top d-flex align-items-center justify-content-center"><i class="bi bi-arrow-up-short"></i></a>

  <?php if ($onSite) { ?>
  <script src="assets/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
  <script src="assets/vendor/isotope-layout/isotope.pkgd.min.js"></script>
  <script src="assets/vendor/waypoints/noframework.waypoints.js"></script>
  <script src="assets/vendor/php-email-form/validate.js"></script>
  <script src="assets/js/main.js"></script>
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
  <script src="assets/js/deviz.js"></script>
  <?php } else { ?>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <?php } ?>

</body>
</html>
