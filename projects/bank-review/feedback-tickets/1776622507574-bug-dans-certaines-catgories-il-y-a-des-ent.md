---
id: 1776622507574
type: bug
status: closed
date: 2026-04-19T18:15:07.574168
project: bank-review
url: https://bank.jlmvpscode.duckdns.org/budget
---

## 🐛 Bug

**Date** : 19/04/2026 18:15
**URL** : `https://bank.jlmvpscode.duckdns.org/budget`

### Description

Dans certaines catégories il y a des entrées positives qui sont comptées négativement. Par exemple le virement des finances publiques de janvier 2026 est compté en négatif dans la ligne "Impôts". 

A mon avis le plus simple est de garder le signe du montant de la dépense et d'afficher des - dans le tableau de dépenses. Pas besoin de distinguer revenu et dépenses

### Contexte

- **User-Agent** : Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0
