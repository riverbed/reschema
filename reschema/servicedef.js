/**
 # Copyright (c) 2019 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the MIT License
 # accompanying the software ("License").  This software is distributed "AS IS"
 # as set forth in the License.
 */

function set_favicon() {
    var link = document.createElement('link');
    link.type = 'image/png';
    link.rel = 'icon';
    link.href = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACyUlEQVQ4jX2TT2hUVxTGv3vunTfmqUSNzMSaLupCEEGK0RI0i7RoKV0UF4JuXHRX1F1WUrpQEIpYulBXaguC6ELsQjAtsaClgrQWM1EkSprEqNFMMpPMy+Q577177+cifxpR+8HZHPh9H+ccjiKJBVW+/yrAquLnME1fs17tUHG11aVJPUrcwMx09Vq5MnUuLyh3XX7qFxhFEpUf9guNKZg1befdk3ufufKIgUsFJEiAoKcSHzsp9w5F3csNrh7ombAAIABAk2s1q9f1ZqXru9zYowA2MVAiEC1KaxERowETqqx1V1vwc/9EcvD0p6sNAOjDTaXAFD+6lJV+/YSzNQ16gQ4QfnEI+e17YMceYVnHXkjYrDg5ClHetDbpzosD8d3xX04OG9Vc+NIO/dPFOBLQCwAobRBs3AnTtgm5De2Q/HLM/n4WeAjRCn7dSgk3teS+G6jaOwKTP+AnRw28k8VtKgVoDWgDP11GdKEbad9vgCcUIHkRaS8GWwdr2VbDerUDLv0PXiqXoX7lKNz4v4DLABJKKYgiiqE2o5HrNCquFrDklG8aWPjpF4BN32grQIK5yPXi0iR+Hw8Q7zL3AGJLJI5eosQNEPRvw++xJOEJP1KzmM04LDNR7RqVeM4Z/z88Xw3r8edYMt1kcEcmK1M/xVZNOk9P0nMuBnAOdG5xBM6np46+byL1t541bhZD3S902cvLD6e6ZzOmGQGSns4ifXwbSakXtClILsJDNevPlOqDqeOPf4+nkSKJs7tbTP9E+s2+jeHxD1boMJ/LiRgDBQidg3XWN6zHvXJqz/TNDD6eskc+LgTXe0ZeWbXwjSc6V5k/niddm9fmvm0v5LcVQwnyRqGeEk8ii9tjSfXW88aNzPHU5pbgbs/IKw/Mf+OCju1olpd1t+J+JdvyInadimp94uhjy+GWZfLXhyv1gxujjWjpYl8DXzKT/bfvmx0AAAAASUVORK5CYII%3D';
    document.getElementsByTagName('head')[0].appendChild(link);
};

function showtab(basename, which)
{
    var lis=document.getElementById(basename+"-tabbar").childNodes; //gets all the LI from the UL

    for(i=0;i<lis.length;i++)
    {
        lis[i].className=""; //removes the classname from all the LI
    }

    var selitem=document.getElementById(basename+"-tab-"+which)
    selitem.className="selected"; //the clicked tab gets the classname selected

    var contents=document.getElementById(basename+"-tabcontent");  //the resource for the main tabContent
    contents.innerHTML = document.getElementById(basename+"-"+which).innerHTML;
}
