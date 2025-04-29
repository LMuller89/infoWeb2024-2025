# 📌 Repositório: InformaticaWeb 2024-2025

## 📚 Sobre o Projeto
Este repositório faz parte das atividades do curso **Técnico em Informática para Web** no Senac PR (2024-2025). Aqui, os alunos irão colaborar em projetos, praticar conceitos de versionamento com GitHub e desenvolver aplicações web.

## 🚀 Como Clonar e Configurar no VS Code
Para começar a trabalhar com este repositório no **VS Code**, siga os passos abaixo:

1. **Abra o terminal no VS Code** (`Ctrl + ` `), e para verificar a versão é aplicando:**
   ```bash
   git --version
   ```
2. **Para o login pela primeira vez, deve aplicar os seguintes códigos**
   ```bash
   git config --global user.name "Seu Nome"
   git config --global user.email "seuemail@exemplo.com"
   ```
3. **Clone o repositório (se for instrutor) ou seu fork (se for aluno):**
   ```bash
   git clone https://github.com/Luciano/informaticaWeb2024-2025.git
   ```
   Se você for aluno e fez um fork, substitua `Luciano` pelo seu nome de usuário no GitHub.
4. **Entre na pasta do projeto:**
   ```bash
   cd informaticaWeb2024-2025
   ```
5. **Abra o projeto no VS Code:**
   ```bash
   code .
   ```

## 🔄 Mantendo o Fork Atualizado (Para Alunos)
Se você fez um **fork**, precisa sincronizá-lo com o repositório original regularmente:
```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

## 🛠 Fluxo de Trabalho no GitHub
1. **Criar uma branch para a nova funcionalidade ou correção:**
   ```bash
   git checkout -b minha-feature
   ```
2. **Fazer alterações no código e adicionar os arquivos alterados:**
   ```bash
   git add .
   ```
3. **Criar um commit com uma mensagem descritiva:**
   ```bash
   git commit -m "Descrição da alteração"
   ```
4. **Enviar as alterações para o GitHub:**
   ```bash
   git push origin minha-feature
   ```
5. **Criar um Pull Request no GitHub para mesclar as mudanças.**

## 📢 Regras de Contribuição
- Sempre crie uma nova branch antes de começar uma alteração.
- Escreva commits claros e descritivos.
- Mantenha o código organizado e bem documentado.
- Antes de enviar um Pull Request, certifique-se de que seu código está atualizado com o repositório original.

---

📌 **Dúvidas?** Entre em contato com o instrutor Luciano ou abra uma **issue** no repositório. Vamos desenvolver juntos! 🚀
