# Neuro-Karaoke-Archive-Metadata


This repository is a public interface for the metadata in the [Neuro Karaoke Archive V3](https://drive.google.com/drive/folders/1B1VaWp-mCKk15_7XpFnImsTdBJPOGx7a). Every so often the archive is updated based on the repo.



## How To Contribute:
* Please read our Style Guidelines before making a submission;
* Our main source of metadata should be [MusicBrainz](https://musicbrainz.org) moving forwards with this project;
* Make an issue or a pull request explaining the problem and the proposed solution;
* Ideally, you should include the relevant MusicBrainz page in the submission;
* You can also help by improving and expanding the README.



## Style Guidelines:


* Date: Release date of the song if there is one. For unreleased songs, they should have the earliest date in which they were publicly available.
The dates should follow the YYYY-MM-DD format.
* Title: The title of the song, if it’s in a non-latin alphabet it should be followed by a parenthesis containing the translation / transcription.
Example: デビルじゃないもん ((Not) A Devil)
* CoverArtist: The singer may be Neuro or Evil for a solo song;
In the case of a duet the singers must be separated by an ‘&’. Neuro should always come before Evil and Evil always before any other duet partner.
Example: “Evil & Cerber”
* Version: For Neuro songs, we have :
"_major_version_._minor_version_".

    _major_version_ : Refers to the major singing upgrades Neuro has received, '1' and '2' are dedicated to albums 1 and 2 respectively, for the newer albums '3' is used.

    _minor_version_ : Indicates if that version of the song already exists in a given _major_version_; The first occurrence is omitted, so for new songs you would find only v3, after that it becomes v3.2.
    
For Evil Neuro and duets they more simply use just the minor version, as there are no major versions attached to them.
* Discnumber: Disc / Album number;
* Track: Number that marks a song position inside its album, should follow release order whenever possible. For completed albums it should have the total track as well. Example:  33/205
* Comment: Unspecified comment, can be used to add extra information such as a song being unreleased.
* Special: Binary that marks whether a song is special or not, as of now the specials include any non-twin duet and the anniversary mixes.
* xxHash: Hash of the audio content of a song. The repository contains the code used to generate the hashes. You should not change this unless you know exactly what you are doing.


## To-Do List:
- [X] Make so that changes to the hjson reflect on the drive;
- [X] Make a proper readme;
- [ ] Add old suggestions as issues / pull requests;
- [X] Make so that the hjson file are automatically renamed to match the new data;
- [ ] Maybe add search for discrepancies?
(i.e. changing "Supercell" to "supercell" checks if all other all instances of "Supercell" were changed as well)