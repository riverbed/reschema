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
