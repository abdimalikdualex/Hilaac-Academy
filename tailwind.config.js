/** @type {import('tailwindcss').Config} */

module.exports = {

  content: [

    "./templates/**/*.html",

    "./apps/**/templates/**/*.html",

    "./apps/**/*.py",

  ],

  darkMode: "class",

  theme: {

    extend: {

      colors: {

        primary: {

          50: "#eef3fa",

          100: "#d5e3f4",

          200: "#abc7e9",

          300: "#7da5d9",

          400: "#4f83c9",

          500: "#1E4D8F",

          600: "#1a437d",

          700: "#16386a",

          800: "#122d57",

          900: "#0B1736",

        },

        accent: {

          400: "#e4bc3a",

          500: "#D4A017",

          600: "#b88914",

        },

        teal: {

          400: "#3fc4b8",

          500: "#0FAE9D",

          600: "#0c8f81",

        },

        surface: {

          light: "#F5F7FA",

        },

      },

      backgroundImage: {

        "hero-education": "url('/static/images/hero-education.svg')",

        "pattern-dots": "url('/static/images/pattern-education.svg')",

        "pattern-books": "url('/static/images/pattern-books.svg')",

      },

    },

  },

  plugins: [],

};


