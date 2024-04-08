#!/bin/bash

subject_list_file="/home2/anirudhkaushik/Brain2Word_paper/subject_list.txt"
while read line
do
      subject=$line
      wget -P "/ssd_scratch/cvit/anirudhkaushik/subject/" ${subject} &
done < $subject_list_file
