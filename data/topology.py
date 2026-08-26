# -*- coding: utf-8 -*-
"""
Topologie du réseau métro parisien (16 lignes).

Ces données (ordre des stations, couleurs officielles) sont compilées à partir
de la connaissance publique du réseau RATP, PAS extraites d'un jeu de données
officiel (le bac à sable de build n'a pas accès à data.iledefrance-mobilites.fr).

Les COORDONNÉES réelles et les IDENTIFIANTS techniques (StopPoint, LineRef) sont
en revanche récupérés en direct depuis l'open data officiel par build_network.py,
qui tourne sur VOTRE machine (donc avec un accès réseau normal).

Si une station manque ou est mal placée dans l'ordre, corrigez simplement la
liste ci-dessous : c'est un fichier texte lisible, pas un format propriétaire.

Chaque ligne est définie par :
  - "color": couleur officielle RATP (hex)
  - "trunk": liste ordonnée des stations du tronc commun (terminus à terminus,
             ou jusqu'à l'embranchement pour les lignes en Y)
  - "branches": (optionnel) liste d'embranchements, chacun avec un nom et la
                liste des stations à la suite du tronc commun
"""

LINES = {
    "1": {
        "name": "1",
        "color": "#FFCD00",
        "trunk": [
            "La Défense", "Esplanade de La Défense", "Pont de Neuilly", "Les Sablons",
            "Porte Maillot", "Argentine", "Charles de Gaulle - Étoile", "George V",
            "Franklin D. Roosevelt", "Champs-Élysées - Clemenceau", "Concorde", "Tuileries",
            "Palais Royal - Musée du Louvre", "Louvre - Rivoli", "Châtelet", "Hôtel de Ville",
            "Saint-Paul", "Bastille", "Gare de Lyon", "Reuilly - Diderot", "Nation",
            "Porte de Vincennes", "Saint-Mandé", "Bérault", "Château de Vincennes",
        ],
    },
    "2": {
        "name": "2",
        "color": "#003CA6",
        "trunk": [
            "Porte Dauphine", "Victor Hugo", "Charles de Gaulle - Étoile", "Ternes",
            "Courcelles", "Monceau", "Villiers", "Rome", "Place de Clichy", "Blanche",
            "Pigalle", "Anvers", "Barbès - Rochechouart", "La Chapelle", "Stalingrad",
            "Jaurès", "Colonel Fabien", "Belleville", "Couronnes", "Ménilmontant",
            "Père Lachaise", "Philippe Auguste", "Alexandre Dumas", "Avron", "Nation",
        ],
    },
    "3": {
        "name": "3",
        "color": "#837902",
        "trunk": [
            "Pont de Levallois - Bécon", "Anatole France", "Louise Michel", "Porte de Champerret",
            "Pereire", "Wagram", "Malesherbes", "Courcelles", "Villiers", "Europe",
            "Saint-Lazare", "Havre - Caumartin", "Opéra", "Quatre-Septembre", "Bourse",
            "Sentier", "Réaumur - Sébastopol", "Arts et Métiers", "République", "Temple",
            "Rue Saint-Maur", "Parmentier", "Rue des Boulets", "Nation", "Porte de Bagnolet",
            "Gallieni",
        ],
    },
    "3bis": {
        "name": "3bis",
        "color": "#6EC4E8",
        "trunk": ["Gambetta", "Pelleport", "Saint-Fargeau", "Porte des Lilas"],
    },
    "4": {
        "name": "4",
        "color": "#CF009E",
        "trunk": [
            "Porte de Clignancourt", "Simplon", "Marcadet - Poissonniers", "Château Rouge",
            "Barbès - Rochechouart", "Gare du Nord", "Gare de l'Est", "Château d'Eau",
            "Strasbourg - Saint-Denis", "Réaumur - Sébastopol", "Étienne Marcel", "Les Halles",
            "Châtelet", "Cité", "Saint-Michel", "Odéon", "Saint-Germain-des-Prés",
            "Saint-Sulpice", "Saint-Placide", "Montparnasse - Bienvenüe", "Vavin", "Raspail",
            "Denfert-Rochereau", "Mouton-Duvernet", "Alésia", "Porte d'Orléans",
            "Mairie de Montrouge", "Barbara", "Bagneux - Lucie Aubrac",
        ],
    },
    "5": {
        "name": "5",
        "color": "#FF7E2E",
        "trunk": [
            "Bobigny - Pablo Picasso", "Bobigny - Pantin - Raymond Queneau", "Église de Pantin",
            "Hoche", "Porte de Pantin", "Ourcq", "Laumière", "Jaurès", "Stalingrad",
            "Gare du Nord", "Gare de l'Est", "Jacques Bonsergent", "République", "Oberkampf",
            "Richard-Lenoir", "Bréguet - Sabin", "Bastille", "Quai de la Rapée",
            "Gare d'Austerlitz", "Saint-Marcel", "Campo-Formio", "Place d'Italie",
        ],
    },
    "6": {
        "name": "6",
        "color": "#6ECA97",
        "trunk": [
            "Charles de Gaulle - Étoile", "Kléber", "Boissière", "Trocadéro", "Passy",
            "Bir-Hakeim", "Dupleix", "La Motte-Picquet - Grenelle", "Cambronne",
            "Sèvres - Lecourbe", "Pasteur", "Montparnasse - Bienvenüe", "Edgar Quinet",
            "Raspail", "Denfert-Rochereau", "Saint-Jacques", "Glacière", "Corvisart",
            "Place d'Italie", "Nationale", "Chevaleret", "Quai de la Gare", "Bercy",
            "Dugommier", "Daumesnil", "Bel-Air", "Picpus", "Nation",
        ],
    },
    "7": {
        "name": "7",
        "color": "#FA9ABA",
        "trunk": [
            "La Courneuve - 8 Mai 1945", "Fort d'Aubervilliers", "Aubervilliers - Pantin - Quatre Chemins",
            "Porte de la Villette", "Corentin Cariou", "Crimée", "Riquet", "Stalingrad",
            "Louis Blanc", "Château-Landon", "Gare de l'Est", "Poissonnière", "Cadet",
            "Le Peletier", "Chaussée d'Antin - La Fayette", "Opéra", "Pyramides",
            "Palais Royal - Musée du Louvre", "Pont Neuf", "Châtelet", "Pont Marie",
            "Sully - Morland", "Jussieu", "Place Monge", "Censier - Daubenton", "Les Gobelins",
            "Place d'Italie", "Tolbiac", "Maison Blanche",
        ],
        "branches": [
            {
                "name": "Mairie d'Ivry",
                "stations": ["Porte de Choisy", "Porte d'Ivry", "Pierre et Marie Curie", "Mairie d'Ivry"],
            },
            {
                "name": "Villejuif - Louis Aragon",
                "stations": [
                    "Le Kremlin-Bicêtre", "Villejuif - Léo Lagrange",
                    "Villejuif - Paul Vaillant-Couturier", "Villejuif - Louis Aragon",
                ],
            },
        ],
    },
    "7bis": {
        "name": "7bis",
        "color": "#6ECA97",
        "trunk": [
            "Louis Blanc", "Bolivar", "Buttes Chaumont", "Botzaris", "Place des Fêtes",
            "Danube", "Pré Saint-Gervais",
        ],
    },
    "8": {
        "name": "8",
        "color": "#E19BDF",
        "trunk": [
            "Balard", "Lourmel", "Boucicaut", "Félix Faure", "Commerce",
            "La Motte-Picquet - Grenelle", "École Militaire", "La Tour-Maubourg", "Invalides",
            "Concorde", "Madeleine", "Opéra", "Richelieu - Drouot", "Grands Boulevards",
            "Bonne Nouvelle", "Strasbourg - Saint-Denis", "République", "Filles du Calvaire",
            "Saint-Sébastien - Froissart", "Chemin Vert", "Bastille", "Ledru-Rollin",
            "Faidherbe - Chaligny", "Reuilly - Diderot", "Montgallet", "Daumesnil",
            "Michel Bizot", "Porte Dorée", "Porte de Charenton", "Liberté",
            "Charenton - Écoles", "École Vétérinaire de Maisons-Alfort", "Maisons-Alfort - Stade",
            "Maisons-Alfort - Les Juilliottes", "Créteil - L'Échat", "Créteil - Université",
            "Créteil - Préfecture",
        ],
    },
    "9": {
        "name": "9",
        "color": "#B6BD00",
        "trunk": [
            "Pont de Sèvres", "Billancourt", "Marcel Sembat", "Porte de Saint-Cloud",
            "Église d'Auteuil", "Michel-Ange - Auteuil", "Michel-Ange - Molitor", "Jasmin",
            "Ranelagh", "La Muette", "Rue de la Pompe", "Trocadéro", "Iéna", "Alma - Marceau",
            "Franklin D. Roosevelt", "Saint-Philippe-du-Roule", "Miromesnil", "Saint-Augustin",
            "Havre - Caumartin", "Chaussée d'Antin - La Fayette", "Richelieu - Drouot",
            "Grands Boulevards", "Bonne Nouvelle", "Strasbourg - Saint-Denis", "République",
            "Oberkampf", "Saint-Ambroise", "Voltaire", "Charonne", "Rue des Boulets", "Nation",
            "Buzenval", "Maraîchers", "Porte de Montreuil", "Robespierre", "Croix de Chavaux",
            "Mairie de Montreuil",
        ],
    },
    "10": {
        "name": "10",
        "color": "#C9910D",
        "trunk": [
            "Boulogne - Pont de Saint-Cloud", "Boulogne - Jean Jaurès", "Michel-Ange - Molitor",
            "Michel-Ange - Auteuil", "Église d'Auteuil", "Chardon-Lagache", "Mirabeau",
            "Javel - André Citroën", "Charles Michels", "Avenue Émile Zola",
            "La Motte-Picquet - Grenelle", "Ségur", "Duroc", "Vaneau", "Sèvres - Babylone",
            "Mabillon", "Odéon", "Cluny - La Sorbonne", "Maubert - Mutualité",
            "Cardinal Lemoine", "Jussieu", "Gare d'Austerlitz",
        ],
    },
    "11": {
        "name": "11",
        "color": "#704B1C",
        "trunk": [
            "Châtelet", "Hôtel de Ville", "Rambuteau", "Arts et Métiers", "République",
            "Goncourt", "Belleville", "Pyrénées", "Jourdain", "Place des Fêtes", "Télégraphe",
            "Porte des Lilas", "Mairie des Lilas", "Serge Gainsbourg", "Romainville - Carnot",
            "Montreuil - Hôpital", "Rosny - Bois-Perrier",
        ],
    },
    "12": {
        "name": "12",
        "color": "#007852",
        "trunk": [
            "Mairie d'Issy", "Corentin Celton", "Porte de Versailles", "Convention", "Vaugirard",
            "Volontaires", "Pasteur", "Falguière", "Montparnasse - Bienvenüe",
            "Notre-Dame-des-Champs", "Rennes", "Saint-Placide", "Sèvres - Babylone",
            "Rue du Bac", "Solférino", "Assemblée Nationale", "Concorde", "Madeleine",
            "Saint-Lazare", "Trinité - d'Estienne d'Orves", "Pigalle", "Abbesses",
            "Lamarck - Caulaincourt", "Jules Joffrin", "Marx Dormoy", "Marcadet - Poissonniers",
            "Porte de la Chapelle", "Front Populaire", "Fort d'Aubervilliers", "Aimé Césaire",
            "Mairie d'Aubervilliers",
        ],
    },
    "13": {
        "name": "13",
        "color": "#6EC4E8",
        "trunk": [
            "Châtillon - Montrouge", "Malakoff - Plateau de Vanves", "Malakoff - Rue Étienne Dolet",
            "Porte de Vanves", "Plaisance", "Pernety", "Gaîté", "Montparnasse - Bienvenüe",
            "Duroc", "Saint-François-Xavier", "Varenne", "Invalides",
            "Champs-Élysées - Clemenceau", "Miromesnil", "Saint-Lazare", "Liège",
            "Place de Clichy", "La Fourche", "Brochant", "Porte de Clichy",
        ],
        "branches": [
            {
                "name": "Asnières - Genevilliers - Les Courtilles",
                "stations": ["Gabriel Péri", "Asnières - Genevilliers - Les Courtilles"],
            },
            {
                "name": "Saint-Denis - Université",
                "stations": [
                    "Mairie de Clichy", "Saint-Ouen", "Garibaldi", "Carrefour Pleyel",
                    "Saint-Denis - Porte de Paris", "Basilique de Saint-Denis", "Saint-Denis - Université",
                ],
            },
        ],
    },
    "14": {
        "name": "14",
        "color": "#62259D",
        "trunk": [
            "Saint-Denis - Pleyel", "Mairie de Saint-Ouen", "Saint-Ouen", "Porte de Clichy",
            "Pont Cardinet", "Saint-Lazare", "Madeleine", "Pyramides", "Châtelet",
            "Gare de Lyon", "Bercy", "Cour Saint-Émilion", "Bibliothèque François Mitterrand",
            "Olympiades", "Maison Blanche", "Hôpital Bicêtre", "Villejuif - Institut Gustave Roussy",
            "L'Haÿ-les-Roses", "Chevilly-Larue", "Thiais - Orly", "Aéroport d'Orly",
        ],
    },
}
