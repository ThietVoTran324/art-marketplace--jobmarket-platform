<template>
  <div class="bg-black text-white font-sans z-30">

    <nav class="fixed top-0 left-0 w-full bg-black bg-opacity-50 backdrop-blur-lg p-6 z-50">
      <div class="flex justify-center items-center max-w-6xl mx-auto gap-2">
        <a href="#hero"
          class="flex items-center gap-2 text-white text-2xl font-semibold hover:text-indigo-400 px-6 py-2 transition-all"
          @click.prevent="scrollTo('#hero')">
          <HomeIcon class="w-5 h-5" /> Home
        </a>
        <a href="#about"
          class="flex items-center gap-2 text-white text-2xl font-semibold hover:text-indigo-400 px-6 py-2 transition-all"
          @click.prevent="scrollTo('#about')">
          <UserIcon class="w-5 h-5" /> About
        </a>
        <a href="#skills"
          class="flex items-center gap-2 text-white text-2xl font-semibold hover:text-indigo-400 px-6 py-2 transition-all"
          @click.prevent="scrollTo('#skills')">
          <CpuIcon class="w-5 h-5" /> Skills
        </a>
        <a href="#services"
          class="flex items-center gap-2 text-white text-2xl font-semibold hover:text-indigo-400 px-6 py-2 transition-all"
          @click.prevent="scrollTo('#services')">
          <HammerIcon class="w-5 h-5" /> Services
        </a>
        <a href="#projects"
          class="flex items-center gap-2 text-white text-2xl font-semibold hover:text-indigo-400 px-6 py-2 transition-all"
          @click.prevent="scrollTo('#projects')">
          <LayoutDashboardIcon class="w-5 h-5" /> Projects
        </a>
        <a href="#experience"
          class="flex items-center gap-2 text-white text-2xl font-semibold hover:text-indigo-400 px-6 py-2 transition-all"
          @click.prevent="scrollTo('#experience')">
          <BriefcaseIcon class="w-5 h-5" /> Experience
        </a>
        <a href="#achievements"
          class="flex items-center gap-2 text-white text-2xl font-semibold hover:text-indigo-400 px-6 py-2 transition-all"
          @click.prevent="scrollTo('#achievements')">
          <TrophyIcon class="w-5 h-5" /> Achievements
        </a>
        <a href="#contact"
          class="flex items-center gap-2 text-white text-2xl font-semibold hover:text-indigo-400 px-6 py-2 transition-all"
          @click.prevent="scrollTo('#contact')">
          <MailIcon class="w-5 h-5" /> {{ t('portfolio.contact') }}
        </a>
      </div>
    </nav>

    <canvas ref="canvasRef" class="fixed inset-0"></canvas>

    <section id="hero"
      class="min-h-screen  flex flex-col items-center justify-center text-center px-6 py-20 overflow-hidden z-50"
      data-aos="zoom-in">
      <svg xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" viewBox="0 0 1920 1080"
        class="absolute top-0 left-0 w-full h-full opacity-30 pointer-events-none z-0 animate-pulse scale-150">
        <defs>
          <linearGradient id="grad-hero" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#6366F1" stop-opacity="1" />
            <stop offset="100%" stop-color="#EC4899" stop-opacity="1" />
          </linearGradient>
          
          <filter id="neon-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g stroke="url(#grad-hero)" stroke-width="3" stroke-opacity="0.5" fill="none" filter="url(#neon-glow)">
          <path d="M0,600 Q480,300 960,600 T1920,600" />
          <path d="M0,700 Q480,400 960,700 T1920,700" />
        </g>
      </svg>

      <h1
        class="z-50 text-6xl font-extrabold bg-clip-text   text-indigo-400 mb-4 "
        style="line-height: 1.2;">
        Daniil Kupryianchyk
      </h1>
      <h2 class="z-10 text-3xl font-semibold text-indigo-400 mb-6">
        Python Backend Developer
      </h2>
      <a href="/CV_Daniil_Kupryianchyk_Python_Backend.pdf" download
        class="z-50 inline-block mt-4 px-6 py-3 rounded-full border border-indigo-400 bg-indigo-500 text-white font-semibold shadow-md hover:bg-indigo-600 hover:shadow-lg transition duration-300">
        📄 {{ t('portfolio.downloadCv') }}
      </a>
    </section>

    <div class="background-gradient"></div>

    <section id="about" class="px-6 py-20 w-full" data-aos="fade-up">
      <h2
        class="text-5xl font-extrabold mb-10 text-center text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-red-400">
        {{ t('portfolio.aboutMe') }}
      </h2>
      <div class="flex flex-col md:flex-row gap-8 items-center justify-center">
        <div
          class="bg-gradient-to-r from-indigo-500 to-purple-500 p-6 rounded-2xl shadow-xl transform hover:scale-105 transition duration-300 ease-in-out max-w-3xl w-full">
          <div class="flex justify-center mb-6">
            <img src="/avatar.png" alt="Profile"
              class="w-48 h-48 object-cover rounded-full shadow-xl border-4 border-indigo-400">
          </div>
          <p class="text-xl text-white font-semibold text-center leading-relaxed">
            Passionate backend developer specializing in scalable and efficient Python applications. I love building
            APIs, automating processes, and designing backend systems using modern tools like FastAPI, PostgreSQL,
            Docker, and Celery.
          </p>
        </div>
      </div>
    </section>

    <section id="skills"
      class="px-6 py-20 w-full bg-gradient-to-r from-indigo-700/50 via-purple-600/90 to-pink-500/50 text-white" style="
    background: linear-gradient(to right, rgba(79, 70, 229, 0.2), rgba(147, 51, 234, 0.5), rgba(236, 72, 153, 0.5));
    -webkit-mask-image: linear-gradient(to bottom, transparent, white 10%, white 90%, transparent);
    mask-image: linear-gradient(to bottom, transparent, white 10%, white 90%, transparent);
  " data-aos="fade-up">
      <h2 class="text-5xl font-extrabold mb-16 text-center">{{ t('portfolio.sections.skills') }}</h2>

      <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
        <!-- Backend -->
        <div
          class="bg-black p-6 rounded-2xl shadow-lg border-2 border-indigo-500 hover:shadow-2xl hover:scale-[1.02] transition">
          <h3 class="text-2xl font-bold text-indigo-400 mb-4">
            🐍 Backend
            <span class="text-sm bg-indigo-500 text-white px-2 py-1 rounded-full ml-2">Main Stack</span>
          </h3>
          <hr class="border-indigo-500 mb-4">
          <ul class="space-y-2 text-lg">
            <li>⚡ FastAPI, Mail, Cache, Limiter</li>
            <li>🛠️ SQLAlchemy, Alembic, Pydantic</li>
            <li>🐍 Celery + Beat, RabbitMQ</li>
            <li>🔑 JWT + OAuth2</li>
            <li>🌀 AsyncIO, Redis (Pub/Sub, Streams), Httpx</li>
            <li>🍓 Strawberry GraphQL, SSE, WebSockets</li>
            <li>🧪 Pytest, 🦊 Ruff, Logging</li>
          </ul>
        </div>

        <!-- Deployment -->
        <div
          class="bg-black p-6 rounded-2xl shadow-lg border-2 border-indigo-500 hover:shadow-2xl hover:scale-[1.02] transition">
          <h3 class="text-2xl font-bold text-indigo-400 mb-4">
            🚀 Deployment
            <span class="text-sm bg-indigo-500 text-white px-2 py-1 rounded-full ml-2">Main Stack</span>
          </h3>
          <hr class="border-indigo-500 mb-4">
          <ul class="space-y-2 text-lg">
            <li>🐳 Docker, Compose</li>
            <li>🌐 Nginx, VPS/VDS</li>
            <li>⚙️ GitLab CI/CD, GitHub CI/CD</li>
            <li>🔒 SSL, Sentry</li>
            <li>📈 Prometheus, Grafana, Loki, Promtail</li>
            <li>☁️ Yandex Cloud (S3), Google Cloud (OAuth2)</li>
            <li>🌀 Git</li>
          </ul>
        </div>

        <!-- Databases -->
        <div
          class="bg-black p-6 rounded-2xl shadow-lg border-2 border-indigo-500 hover:shadow-2xl hover:scale-[1.02] transition">
          <h3 class="text-2xl font-bold text-indigo-400 mb-4">
            🗄️ Databases
            <span class="text-sm bg-indigo-500 text-white px-2 py-1 rounded-full ml-2">Main Stack</span>
          </h3>
          <hr class="border-indigo-500 mb-4">
          <ul class="space-y-2 text-lg">
            <li>🐘 PostgreSQL</li>
            <li>💾 MySQL</li>
            <li>🔴 Redis</li>
            <li>🍃 MongoDB</li>
          </ul>
        </div>

        <!-- Frontend -->
        <div
          class="bg-black p-6 rounded-2xl shadow-lg border border-indigo-400 hover:shadow-2xl hover:scale-[1.02] transition">
          <h3 class="text-2xl font-bold text-indigo-400 mb-4">🎨 Frontend</h3>
          <hr class="border-indigo-400 mb-4">
          <ul class="space-y-2 text-lg">
            <li>🌐 Vue.js + Router</li>
            <li>📦 Pinia, 💨 Tailwind CSS</li>
            <li>📡 Axios</li>
          </ul>
        </div>

        <!-- Other Experience -->
        <div
          class="bg-black p-6 rounded-2xl shadow-lg border border-indigo-400 hover:shadow-2xl hover:scale-[1.02] transition">
          <h3 class="text-2xl font-bold text-indigo-400 mb-4">🛠️ Other Experience</h3>
          <hr class="border-indigo-400 mb-4">
          <ul class="space-y-2 text-lg">
            <li>🎭 Django, DRF</li>
            <li>🍶 Flask</li>
            <li>🌍 Aiohttp</li>
            <li>🤖 Aiogram</li>
          </ul>
        </div>

        <!-- English -->
        <div
          class="bg-black p-6 rounded-2xl shadow-lg border border-indigo-400 hover:shadow-2xl hover:scale-[1.02] transition">
          <h3 class="text-2xl font-bold text-indigo-400 mb-4">🗣️ English Level</h3>
          <hr class="border-indigo-400 mb-4">
          <p class="text-lg">A2+ (Pre-Intermediate)</p>
        </div>
      </div>
    </section>

    <section id="services" class="bg-gradient-to-br  bg-black/50 text-white py-2 px-6" data-aos="fade-up">
      <div class="max-w-7xl mx-auto">
        <h2 class="text-5xl font-extrabold text-center text-purple-400 mb-16 tracking-wide mt-20">{{ t('portfolio.sections.services') }}</h2>

        <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-10">

          <div
            class="bg-black rounded-3xl p-8 shadow-2xl hover:shadow-pink-500/90 transition-shadow duration-300 backdrop-blur-xs">
            <LayoutDashboardIcon class="w-10 h-10 text-indigo-400 mb-6" />
            <h3 class="text-2xl font-semibold mb-4 text-white">Web App Development</h3>
            <p class="text-gray-300 text-lg leading-relaxed">
              Fast, responsive & scalable web apps built with cutting-edge tools tailored to your vision.
            </p>
          </div>

          <div
            class="bg-black rounded-3xl p-8 shadow-2xl hover:shadow-yellow-500/90 transition-shadow duration-300 backdrop-blur-xs">
            <GaugeIcon class="w-10 h-10 text-indigo-400 mb-6" />
            <h3 class="text-2xl font-semibold mb-4 text-white">Performance Optimization</h3>
            <p class="text-gray-300 text-lg leading-relaxed">
              Supercharge your backend with caching (Redis), async tasks (Celery), and blazing-fast queries.
            </p>
          </div>

          <div
            class="bg-black rounded-3xl p-8 shadow-2xl hover:shadow-green-500/90 transition-shadow duration-300 backdrop-blur-xs">
            <NetworkIcon class="w-10 h-10 text-indigo-400 mb-6" />
            <h3 class="text-2xl font-semibold mb-4 text-white">Architecture Consulting</h3>
            <p class="text-gray-300 text-lg leading-relaxed">
              Craft secure, modular & scalable systems using Docker, CI/CD, and microservices.
            </p>
          </div>

          <div
            class="bg-black rounded-3xl p-8 shadow-2xl hover:shadow-blue-500/90 transition-shadow duration-300 backdrop-blur-xs">
            <LinkIcon class="w-10 h-10 text-indigo-400 mb-6" />
            <h3 class="text-2xl font-semibold mb-4 text-white">API Development</h3>
            <p class="text-gray-300 text-lg leading-relaxed">
              Robust RESTful & GraphQL APIs plus seamless integration with third-party services.
            </p>
          </div>

        </div>
      </div>
    </section>

    <section id="projects" class="px-0 py-20 bg-black/50 min-h-screen" data-aos="fade-up">
      <h2
        class="text-5xl font-extrabold mb-10 text-center text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500">
        Projects
      </h2>

      <Swiper :modules="[Navigation]" :slides-per-view="1" :loop="true" :navigation="true"
        class="max-w-full mx-auto custom-swiper">
        <SwiperSlide v-for="(project, index) in projects" :key="index"
          class="rounded-xl shadow-xl hover:shadow-indigo-500/50 transition cursor-grab active:cursor-grabbing relative">
          
          <img :src="project.image" alt="Project Image" class="w-full h-screen object-cover rounded-lg" />

          
          <div class="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black via-transparent to-transparent">
            <h3 class="text-2xl font-bold mb-3 text-indigo-400 flex items-center gap-4">
              {{ project.title }}
              <div class="flex items-center gap-4 text-sm text-gray-300"
                v-if="project.stars !== null && project.forks !== null">

                
                <div class="flex items-center gap-1">
                  <svg class="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.286 3.958a1 1 0 0 0 .95.69h4.162c.969 0 1.371 1.24.588 1.81l-3.37 2.448a1 1 0 0 0-.364 1.118l1.285 3.958c.3.922-.755 1.688-1.54 1.118L10 13.347l-3.37 2.448c-.784.57-1.838-.196-1.54-1.118l1.286-3.958a1 1 0 0 0-.364-1.118L2.642 9.385c-.783-.57-.38-1.81.588-1.81h4.162a1 1 0 0 0 .95-.69l1.286-3.958z" />
                  </svg>
                  {{ project.stars }}
                </div>

                
                <div class="flex items-center gap-1">
                  <svg class="w-4 h-4 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
                    <path
                      d="M5 3a3 3 0 1 0 0 6c.35 0 .687-.06 1-.17v2.34a3 3 0 0 0 2 2.83v3.17A3.001 3.001 0 0 0 6 21a3 3 0 1 0 3-3v-3.17a3.001 3.001 0 0 0 2-2.83V8.83A3.001 3.001 0 0 0 15 6a3 3 0 1 0-3-3c0 .35.06.687.17 1H9.83A3.001 3.001 0 0 0 7 6a2.99 2.99 0 0 0-2-.17V3z" />
                  </svg>
                  {{ project.forks }}
                </div>

              </div>
            </h3>

            <p class="text-lg text-white mb-4">{{ project.description }}</p>

            
            <div class="flex flex-wrap gap-2 mb-6">
              <span v-for="tech in project.stack" :key="tech"
                class="px-3 py-1 text-sm font-medium bg-indigo-500/10 text-indigo-300 rounded-full">
                {{ tech }}
              </span>
            </div>

            
            <div class="flex flex-col sm:flex-row sm:items-center gap-4">
              <a :href="project.link" target="_blank" class="text-indigo-400 text-xl hover:underline">
                View on GitHub →
              </a>
              <a v-if="project.demo" :href="project.demo" target="_blank" class="text-pink-400 text-xl hover:underline">
                Live Demo →
              </a>
            </div>
          </div>
        </SwiperSlide>
      </Swiper>
    </section>

    <section id="experience" class="px-6 py-20 max-w-5xl mx-auto bg-black/80" data-aos="fade-right">
      <h2
        class="text-5xl font-extrabold mb-6 text-center text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500">
        Experience
      </h2>
      <div class="border-l-2 border-indigo-500 pl-6">
        <div class="mb-10 border-pink-500 pl-6 border-l-2">
          <h3 class="text-xl font-semibold">Full-Stack Developer – Pinterest Clone</h3>
          <span class="text-sm text-gray-400">Dec 2024 – Present (5 months)</span>
          <p class="text-gray-300 mt-2">
            Developed a Pinterest-like platform with a Vue 3 frontend and FastAPI backend, using PostgreSQL
            (SQLAlchemy, Alembic), MongoDB, and MySQL for databases. Integrated real-time chat wuth websockets, dynamic
            updates with sse, recommendations,
            notifications, tag-based search, authentication using JWT and cookies, many-to-mant complex relationships in
            the database. Utilized Celery for background tasks and Redis Streams for service
            communication. Employed FastAPI Mail and Cache for optimized email workflows and performance. Configured
            GraphQL (Strawberry) for flexible API interactions. Ensured code quality with Ruff, wrote tests with Pytest
            and httpx, and set up GitLab CI/CD for automation. Deployed to a VPS with Nginx and SSL, and integrated
            Yandex S3 for media storage.
          </p>
          <br />
          <div class="flex flex-row items-center gap-4 ">
            <a href="https://github.com/shutsuensha/pint3rest.xyz" target="_blank"
              class="text-indigo-400  hover:underline">
              View on GitHub →
            </a>
            <br />
            <a href="https://pint3rest.xyz" target="_blank" class="text-pink-400 hover:underline">
              Live Demo →
            </a>
          </div>
        </div>

        <div class="border-pink-500 pl-6 border-l-2">
          <h3 class="text-xl font-semibold">Python Developer – TeachMeSkills (Graduation Project)</h3>
          <span class="text-sm text-gray-400">Sep 2024 – Mar 2025 (7 months)</span>
          <p class="text-gray-300 mt-2">
            Built a full-featured e-commerce platform using Django and PostgreSQL as part of a diploma project at
            TeachMeSkills.
            Integrated Google authentication and notifications, developed a custom admin panel, and applied best
            practices in database design and user experience.
            Gained hands-on experience with Django REST Framework, SQLAlchemy, FastAPI, and asynchronous Python
            (asyncio, Aiohttp).
            Practiced unit testing with Pytest and unittest, and collaborated through Git and GitHub workflows
            (branches, pull requests).
          </p>
          <br />
          <div>
            <a href="https://github.com/shutsuensha/online-store" target="_blank"
              class="text-indigo-400 hover:underline">
              View on GitHub →
            </a>
          </div>
        </div>
      </div>
    </section>

    <section id="achievements" class="px-6 py-20" data-aos="fade-up">
      <h2
        class="text-5xl font-extrabold mb-10 text-center text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500">
        Achievements
      </h2>

      
      <Swiper :modules="[Navigation]" spaceBetween="10" slidesPerView="1" navigation :loop="true"
        class="swiper-container cursor-grab active:cursor-grabbing">
        

        <SwiperSlide>
          <div class="flex flex-row gap-6">
            <!-- Certificate 1 -->
            <div class="flex-1">
              <img
                src="https://raw.githubusercontent.com/shutsuensha/shutsuensha/refs/heads/main/FastAPI-ArtemShumeiko-1.png"
                alt="Certificate 1" class="w-full  rounded-lg shadow-md hover:shadow-lg transition-all" />
            </div>

            <!-- Certificate 2 -->
            <div class="flex-1">
              <img
                src="https://raw.githubusercontent.com/shutsuensha/shutsuensha/refs/heads/main/FastAPI-ArtemShumeiko-2.png"
                alt="Certificate 2" class="w-full rounded-lg shadow-md hover:shadow-lg transition-all" />
            </div>
          </div>
        </SwiperSlide>

        <SwiperSlide>
          <div class="text-center">
            <img src="https://raw.githubusercontent.com/shutsuensha/shutsuensha/refs/heads/main/TMS-1.png"
              alt="TeachMeSkills Certificate" class="w-full  rounded-lg shadow-md hover:shadow-lg transition-all" />
          </div>
        </SwiperSlide>

        
      </Swiper>
    </section>

    <footer id="contact" class="bg-black text-white font-sans relative overflow-hidden">
      <!-- Neon Gradient Background -->
      <div class="absolute inset-0 pointer-events-none">
        <svg class="w-full h-full opacity-10" preserveAspectRatio="none" viewBox="0 0 1920 1080">
          <defs>
            <linearGradient id="grad-footer" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#8b5cf6" />
              <stop offset="100%" stop-color="#ec4899" />
            </linearGradient>
            <filter id="footer-blur">
              <feGaussianBlur in="SourceGraphic" stdDeviation="100" />
            </filter>
          </defs>
          <rect width="1920" height="1080" fill="url(#grad-footer)" filter="url(#footer-blur)" />
        </svg>
      </div>

      <div
        class="relative z-10 max-w-5xl mx-auto px-6 py-16 flex flex-col md:flex-row items-center justify-center gap-12">
        
        <div class="space-y-6 text-center md:text-left md:flex-1">
          <h3 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-500">
            Contact me
          </h3>
          <div class="flex justify-center md:justify-start space-x-4">
            <!-- GitHub -->
            <a href="https://github.com/shutsuensha" target="_blank" class="hover:text-purple-400 transition">
              <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                <path
                  d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.799 8.207 11.387.6.111.793-.261.793-.58 0-.285-.011-1.04-.016-2.04-3.338.725-4.042-1.61-4.042-1.61-.546-1.386-1.333-1.754-1.333-1.754-1.089-.745.083-.729.083-.729 1.205.085 1.838 1.237 1.838 1.237 1.07 1.835 2.809 1.305 3.495.997.108-.775.418-1.305.762-1.605-2.665-.304-5.466-1.332-5.466-5.931 0-1.31.469-2.381 1.236-3.221-.124-.303-.536-1.523.117-3.176 0 0 1.008-.322 3.301 1.23a11.5 11.5 0 0 1 3.003-.404c1.018.005 2.045.138 3.003.404 2.291-1.552 3.297-1.23 3.297-1.23.655 1.653.243 2.873.119 3.176.77.84 1.235 1.911 1.235 3.221 0 4.61-2.804 5.625-5.475 5.921.43.372.823 1.103.823 2.222 0 1.604-.014 2.896-.014 3.293 0 .321.192.694.8.576C20.565 21.796 24 17.296 24 12c0-6.63-5.37-12-12-12z" />
              </svg>
            </a>

            <!-- LinkedIn -->
            <a href="https://www.linkedin.com/in/daniil-kupryianchyk-960594322" target="_blank"
              class="hover:text-purple-400 transition">
              <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                <path
                  d="M19 0h-14c-2.761 0-5 2.238-5 5v14c0 2.762 2.239 5 5 5h14c2.762 0 5-2.238 5-5v-14c0-2.762-2.238-5-5-5zm-11 19h-3v-10h3v10zm-1.5-11.271c-.966 0-1.75-.791-1.75-1.765s.784-1.765 1.75-1.765 1.75.791 1.75 1.765-.784 1.765-1.75 1.765zm13.5 11.271h-3v-5.604c0-1.337-.027-3.058-1.865-3.058-1.866 0-2.151 1.46-2.151 2.969v5.693h-3v-10h2.881v1.367h.041c.401-.757 1.379-1.554 2.84-1.554 3.037 0 3.6 1.999 3.6 4.599v5.588z" />
              </svg>
            </a>

            <!-- Telegram -->
            <a href="https://t.me/evalshine" target="_blank" class="hover:text-purple-400 transition">
              <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                <path
                  d="M9.993 15.447l-.405 4.192c.58 0 .83-.25 1.133-.551l2.72-2.604 5.63 4.113c1.03.57 1.761.271 2.03-.951l3.68-17.262c.374-1.73-.631-2.403-1.662-2.009L1.57 9.407c-1.708.682-1.69 1.659-.29 2.107l4.724 1.474 10.953-6.904c.516-.35.99-.158.602.192L9.993 15.447z" />
              </svg>
            </a>

            <!-- Email -->
            <a href="mailto:dankupr21@gmail.com" class="hover:text-purple-400 transition">
              <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 13.065L.857 4.5h22.286L12 13.065zM0 5.932v12.636h24V5.932l-12 9.429L0 5.932z" />
              </svg>
            </a>

            <a href="https://drive.google.com/file/d/1gkMx7bBNnDl95wmoXoW6aj7aF-6VDcPJ/view?usp=sharing" target="_blank"
              class="hover:text-purple-400 transition" :title="t('portfolio.downloadCv')">
              <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                <path
                  d="M14 2H6a2 2 0 0 0-2 2v16c0 1.103.897 2 2 2h12a2 2 0 0 0 2-2V8l-6-6zm1 7H8V8h7v1zm-1 3H8v-1h6v1zm3-6h-5V3.003L17.003 6zM8 15h8v1H8v-1zm0 3h8v1H8v-1z" />
              </svg>
            </a>

          </div>
          <p class="text-gray-400">
            Or send me a message right here:
          </p>
        </div>

        
        <form @submit.prevent="sendMessage" class="space-y-6 w-full md:flex-1">
          <div>
            <label class="block text-sm font-medium mb-2" for="name">Name</label>
            <input v-model="form.name" id="name" type="text" required
              class="w-full px-4 py-2 rounded-xl bg-gray-900 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
          </div>

          <div>
            <label class="block text-sm font-medium mb-2" for="email">Email</label>
            <input v-model="form.email" id="email" type="email" required
              class="w-full px-4 py-2 rounded-xl bg-gray-900 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
          </div>

          <div>
            <label class="block text-sm font-medium mb-2" for="message">Message</label>
            <textarea v-model="form.message" id="message" rows="4" required
              class="w-full px-4 py-2 rounded-xl bg-gray-900 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-500 transition resize-none"></textarea>
          </div>

          <div>
            <label class="block text-sm font-medium mb-2" for="attachment">Attachment</label>
            <input id="attachment" type="file" @change="handleFileUpload"
              class="w-full px-4 py-2 rounded-xl bg-gray-900 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
          </div>

          <button type="submit"
            class="w-full py-3 rounded-full bg-gradient-to-r from-purple-500 to-purple-500 text-white font-semibold hover:from-purple-600 hover:to-pink-600 transition shadow-lg">
            {{ t('portfolio.contactForm.send') }}
          </button>
        </form>
      </div>

      <div class="text-center text-white text-sm pb-6">
        © {{ new Date().getFullYear() }} Daniil Kupryianchyk. All rights reserved.
      </div>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, ref, onBeforeUnmount } from 'vue'
import AOS from 'aos'
import 'aos/dist/aos.css'
import axios from 'axios'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

import { reactive } from 'vue'

import * as THREE from 'three'

const canvasRef = ref(null)

let renderer, scene, camera, points, animationId

const form = ref({
  name: '',
  email: '',
  message: '',
  attachment: null,
})

import { Swiper, SwiperSlide } from 'swiper/vue';
import 'swiper/css';
import 'swiper/css/pagination';
import 'swiper/css/navigation';
import { Pagination, Navigation } from 'swiper/modules';

import JSConfetti from 'js-confetti'

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    form.value.attachment = file
  }
}

const confetti = new JSConfetti()

const sendMessage = async () => {
  try {
    const formData = new FormData()
    formData.append('name', form.value.name)
    formData.append('email', form.value.email)
    formData.append('message', form.value.message)

    if (form.value.attachment) {
      formData.append('file', form.value.attachment)
    }

    const response = await axios.post('/api/contact/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    confetti.addConfetti({
      emojis: ['🌈', '⚡️', '💥', '✨', '💫', '🦄'],
      confettiColors: ['#ff0a54', '#ff477e', '#ff7096', '#ff85a1', '#fbb1bd', '#f9bec7'],
      confettiRadius: 6,
      confettiNumber: 100,
      emojiSize: 40,
      emojiNumber: 50,
      shapes: ['circle', 'square'],
      confettiGravity: 0.5,
      confettiDrift: 0.1,
      confettiStartVelocity: 30,
      confettiAngle: 90,
      confettiSpread: 180,
      confettiDuration: 5000
    })
    form.value.name = ''
    form.value.email = ''
    form.value.message = ''
    form.value.attachment = null
  } catch (error) {
    console.error('Error:', error)
    alert(t('portfolio.contactForm.sendError'))
  }
}

async function fetchRepoStats(repoUrl) {
  try {
    const repoPath = new URL(repoUrl).pathname.slice(1) // 'user/repo'
    const res = await fetch(`https://api.github.com/repos/${repoPath}`)
    if (!res.ok) throw new Error('GitHub API error')
    const data = await res.json()
    return {
      stars: data.stargazers_count,
      forks: data.forks_count
    }
  } catch (err) {
    console.error('Failed to fetch GitHub stats:', err)
    return {
      stars: 0,
      forks: 0
    }
  }
}

onMounted(async () => {
  document.title = "Portfolio - Daniil Kupryianchyk";

  const link = document.querySelector("link[rel='icon']") || document.createElement('link');
  link.rel = 'icon';
  link.href = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><text x="0" y="26" font-size="30">🐰</text></svg>';
  document.head.appendChild(link);

  AOS.init({ once: false, duration: 2000 });

  for (const project of projects.value) {
    const stats = await fetchRepoStats(project.link)
    project.stars = stats.stars
    project.forks = stats.forks
  }

  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 1, 1000)
  camera.position.z = 50

  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    alpha: true,
    antialias: true,
  })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(window.devicePixelRatio)

  const geometry = new THREE.BufferGeometry()
  const vertices = []

  const particleCount = 10000
  for (let i = 0; i < particleCount; i++) {
    const x = (Math.random() - 0.5) * 200
    const y = (Math.random() - 0.5) * 200
    const z = (Math.random() - 0.5) * 200
    vertices.push(x, y, z)
  }

  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))

  const material = new THREE.PointsMaterial({
    color: 0x00ffff,
    size: 0.5,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })

  points = new THREE.Points(geometry, material)
  scene.add(points)

  animate()
  window.addEventListener('resize', onWindowResize)

});

const projects = ref([
  {
    title: 'Pinterest Clone',
    description: 'Full-featured FastAPI backend and Vue 3 frontend with real-time chat, live updates, media uploads, boards, pins, comments, likes, recommendations, and more. Dockerized with CI/CD pipeline. Deployed on VPS with SSL via Nginx.',
    link: 'https://github.com/shutsuensha/pint3rest.xyz',
    image: 'https://raw.githubusercontent.com/shutsuensha/pinterest-clone-vue3-fastapi/refs/heads/main/.github/assets/feed.png',
    stack: [
      'FastAPI', 'FastAPI-Cache', 'FastAPI-Mail', 'FastAPI-Limiter', 'SQLAlchemy', 'Pydantic', 'Pydantic-Settings', 'JWT + OAuth2',
      'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Celery', 'Celery Beat', 'Docker', 'RabbitMQ', 
      'Docker Compose', 'Nginx', 'SSL', 'VPS', 'Yandex S3', 'Httpx', 'WebSockets', 'SSE',
      'AsyncIO', 'Logging', 'Pytest', 'Ruff', 'Alembic', 'GitLab CI/CD',
      'GraphQL (Strawberry)', 'Redis Stream', 'Redis Pub/Sub', 'Vue 3', 'Vue Router', 'Tailwind CSS', 'Pinia', 'Axios', 'Git', 'Sentry', 'Prometheus',
      'Grafana', 'Loki', 'Promtail'
    ],
    demo: 'https://pint3rest.xyz',
    stars: null,
    forks: null
  },
  {
    title: 'Diploma project from TeachMeSkills',
    description: 'Django e-commerce backend, user auth, order tracking, and admin dashboard.',
    link: 'https://github.com/shutsuensha/online-store',
    image: 'https://raw.githubusercontent.com/shutsuensha/online-store/refs/heads/main/assets/screenshots/logo.png',
    stack: ['Django', 'PostgreSQL', 'Tailwind CSS'],
    demo: null,
    stars: null,
    forks: null
  }
])

function scrollTo(selector) {
  const target = document.querySelector(selector)
  if (!target) return

  const offset = 80
  const targetPosition = target.offsetTop - offset
  const startPosition = window.pageYOffset
  const distance = targetPosition - startPosition
  const duration = 1000
  let startTime = null

  function animation(currentTime) {
    if (startTime === null) startTime = currentTime
    const timeElapsed = currentTime - startTime
    const run = ease(timeElapsed, startPosition, distance, duration)
    window.scrollTo(0, run)
    if (timeElapsed < duration) {
      requestAnimationFrame(animation)
    }
  }

  function ease(t, b, c, d) {
    const ts = (t /= d) * t
    const tc = ts * t
    return b + c * (tc + -3 * ts + 3 * t)
  }

  requestAnimationFrame(animation)
}

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onWindowResize)
})

function animate() {
  animationId = requestAnimationFrame(animate)
  points.rotation.x += 0.0005
  points.rotation.y += 0.001
  renderer.render(scene, camera)
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize(window.innerWidth, window.innerHeight)
}
</script>

<style scoped>
section {
  min-height: 100vh;
  padding-top: 100px;
}

body {
  font-family: 'Segoe UI', sans-serif;
}

.animate-pulse {
  animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {

  0%,
  100% {
    opacity: 0.3;
  }

  50% {
    opacity: 1;
  }
}

.custom-swiper .swiper-pagination-bullet {
  background-color: #818cf8 !important;
  /* Tailwind indigo-400 */
  opacity: 1 !important;
}

.custom-swiper .swiper-pagination-bullet-active {
  background-color: #c084fc !important;
  /* Tailwind fuchsia-400 */
}
</style>

<style>
@keyframes pulse-glow {

  0%,
  100% {
    box-shadow: 0 0 20px rgba(255, 255, 255, 0.3);
    transform: translateY(-50%) scale(1);
  }

  50% {
    box-shadow: 0 0 30px rgba(255, 255, 255, 0.6);
    transform: translateY(-50%) scale(1.05);
  }
}

.swiper-button-next,
.swiper-button-prev {
  background-color: rgba(255, 255, 255, 0.15);
  
  backdrop-filter: blur(4px);
  
  border: 2px solid rgba(255, 255, 255, 0.3);
  
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.3);
  
  border-radius: 50%;
  width: 100px;
  height: 100px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  transition: transform 0.3s ease, background-color 0.3s ease, box-shadow 0.3s ease;

  animation: pulse-glow 2.5s infinite ease-in-out;
}

.swiper-button-next {
  right: 50px;
}

.swiper-button-prev {
  left: 50px;
}

.swiper-button-next:hover,
.swiper-button-prev:hover {
  background-color: rgba(255, 255, 255, 0.25);
  
  box-shadow: 0 0 30px rgba(255, 255, 255, 0.6);
  transform: translateY(-50%) scale(1.05);
  
}

.swiper-button-next:after,
.swiper-button-prev:after {
  font-size: 3rem;
  color: #6366f1;
  /* Indigo-500 */
  text-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
}

.swiper-slide {
  position: relative;
}

.swiper-slide .absolute {
  background: linear-gradient(to top, rgba(0, 0, 0, 0.85) 80%, rgba(0, 0, 0, 0) 100%);
}

.neon-text {
  font-size: 5rem;
  color: #fff;
  text-shadow: 0 0 5px #ff00ff, 0 0 10px #ff00ff, 0 0 15px #ff00ff, 0 0 20px #ff00ff, 0 0 25px #ff00ff;
  animation: neon-animation 1.5s infinite alternate;
}

@keyframes neon-animation {
  0% {
    text-shadow: 0 0 5px #ff00ff, 0 0 10px #ff00ff, 0 0 15px #ff00ff, 0 0 20px #ff00ff, 0 0 25px #ff00ff;
  }

  100% {
    text-shadow: 0 0 20px #ff00ff, 0 0 30px #ff00ff, 0 0 40px #ff00ff, 0 0 50px #ff00ff, 0 0 60px #ff00ff;
  }
}
</style>