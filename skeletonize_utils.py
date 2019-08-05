import skimage.morphology as m
import numpy as np
import skimage.draw as draw
import cv2 as cv2
import skimage as skimage
import skimage.io as io
import matplotlib.pyplot as plt
from statistics import mean 
import random

#parameters
NUMBER_OF_DILATIONS = 6
MIN_CONTOUR_AREA = 800
MAX_CONTOUR_AREA = 500000
ADAPTATIVE_THRESHOLD_BLOCK_SIZE = 3
ADAPTATIVE_THRESHOLD_C = 1
CANNY_THRESHOLD = 50
SECTIONS_FOR_FINDING_BRIGHTEDGES=7
SON_PER_AREA_RATIO_THRESHOLD = 1/50

#process a single frame
def process_frame(img, resize_factor, distance_per_pixel,countour_adaptation):
    image_width=int(img.shape[1]/resize_factor)
    image_height=int(img.shape[0]/resize_factor)
    img = cv2.resize(img,(image_width,image_height))

    final_image_bit,final_contours,final_image = image_with_sections_contounered_in_cicle(img,countour_adaptation)

    skeleton = skeletonize(final_image_bit)

    final_joints =  find_joints(skeleton)    
    final_distances = find_distances(skeleton,final_joints)
    final_meshes = find_meshes(final_contours)

    paint_graph(img,final_distances,distance_per_pixel)
    paint_areas(img,final_contours)

    number_of_joints = len(final_joints)    
    
    number_of_meshes = len(final_meshes)
    total_meshes_area = sum(final_meshes)
    average_meshes_area = mean(final_meshes)
    number_of_segments = len(final_distances)
    total_segments_length = sum([item[3] for item in final_distances]) 

    return (img,number_of_joints,number_of_meshes,total_meshes_area,average_meshes_area,number_of_segments,total_segments_length, final_image)


    
#takes the image, finds the circle containing the experiment and the contours
def image_with_sections_contounered_in_cicle(img,countour_adaptation):     

    circle_image_mask = create_internal_circle_mask(img)

    img = cv2.multiply(img, circle_image_mask)

    edges = cv2.Canny(img,CANNY_THRESHOLD,CANNY_THRESHOLD)
    final_sobely = np.uint8(edges)
    final_image = np.zeros([img.shape[0],img.shape[1],1], dtype=np.uint8)
    thresh_gaussian = cv2.adaptiveThreshold(final_sobely,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,ADAPTATIVE_THRESHOLD_BLOCK_SIZE,ADAPTATIVE_THRESHOLD_C)
    (contours,hierarchy) = cv2.findContours(thresh_gaussian,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

    final_contours = [c for idx,c in enumerate(contours) if contour_validation(img,idx,c,hierarchy) ]
    cv2.drawContours(final_image, final_contours, -1, (255), 1)
    cv2.fillPoly(final_image, final_contours, color=(255))
    final_image_bit = skimage.img_as_bool(cv2.bitwise_not(final_image))    
    final_image_bit = np.bitwise_and(final_image_bit,circle_image_mask)
    
    #avoid inner contours by painting everyone in black
    final_image_bit_aux = np.uint8(skimage.img_as_bool(final_image))*255    
    thresh_gaussian = cv2.adaptiveThreshold( final_image_bit_aux,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,ADAPTATIVE_THRESHOLD_BLOCK_SIZE,ADAPTATIVE_THRESHOLD_C)
    (contours,_) = cv2.findContours(thresh_gaussian,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    #final_contours = [c for c in contours if cv2.contourArea(c) > MIN_CONTOUR_AREA*countour_adaptation and cv2.contourArea(c) < MAX_CONTOUR_AREA*countour_adaptation]

    return final_image_bit,contours,final_image

#http://opencvpython.blogspot.com/2012/06/contours-3-extraction.html
def contour_validation(img,idx,contour,hierarchy):

    validated = True
    area = cv2.contourArea(contour)

    if(cv2.contourArea(contour) < MIN_CONTOUR_AREA):
        return False    

    number_of_sons = len([h for h in hierarchy[0] if h[3]==idx ])

    sons_per_area_ratio = number_of_sons/area

    if(sons_per_area_ratio>SON_PER_AREA_RATIO_THRESHOLD):
        return False


    
    #mask = np.zeros(img.shape,np.uint8)
    #cv2.drawContours(mask,[contour],0,255,-1)
    #pixelpoints = np.transpose(np.nonzero(mask))

    #min_val, max_val, min_loc,max_loc = cv2.minMaxLoc(img,mask = mask)
    #mean_val = cv2.mean(img,mask = mask)  

    return validated

#finds a bright point in each side of the image in the middle row and creates a circle max with them
def create_internal_circle_mask(img):
    #take pixels in the middle and find brightest in the first quarter
    image_width=int(img.shape[1])
    image_height=int(img.shape[0])
    sections= SECTIONS_FOR_FINDING_BRIGHTEDGES
    middle_height = int(img.shape[0]/2)
    section_width = int(img.shape[1]/sections)
    left_middle_row = img[middle_height:middle_height+1,0:section_width]
    (_, _, _, max_loc_left) = cv2.minMaxLoc(left_middle_row)
    max_loc_left=max_loc_left[0]

    right_middle_row = img[middle_height:middle_height+1,(image_width-section_width):image_width]
    (_, _, _, max_loc_right) = cv2.minMaxLoc(right_middle_row)
    max_loc_right=max_loc_right[0]+section_width*(sections-1)

    radious=int((max_loc_right-max_loc_left)/2)
    center_x=radious+max_loc_left   
    
    circle_image_mask = np.zeros((image_height,image_width ), dtype=np.uint8)

    rr, cc = draw.circle(center_x, middle_height, radious)

    final_circle_rr = []
    final_circle_cc = []

    for i in range(len(rr)):
        if(rr[i]>=0 and rr[i]<image_width and cc[i]>=0 and cc[i]<image_height):
            final_circle_rr.append(rr[i])
            final_circle_cc.append(cc[i])

    circle_image_mask[ final_circle_cc,final_circle_rr] = 1

    return circle_image_mask


#first it makes dilations to remove some "hair" and later skeletonize the image
def skeletonize(img):
    skeleton = img
    for _ in range(NUMBER_OF_DILATIONS):
        skeleton = m.binary_dilation(skeleton)

    skeleton = m.skeletonize(skeleton)

    return skeleton

#find the joints in a skeleton looking for pixels that are sorounded by 3 or more pixels
def find_joints(img):
    # Find row and column locations that are non-zero
    (rows,cols) = np.nonzero(img)

    # Initialize empty list of co-ordinates
    skel_coords = []

    # For each non-zero pixel...
    for (r,c) in zip(rows,cols):

        number_of_neighbours = len(list(find_neighbours(img, (r,c),[])))

        # If the number of non-zero locations equals 2, add this to 
        # our list of co-ordinates
        if number_of_neighbours > 2:
            skel_coords.append((r,c,number_of_neighbours))
    
    items_to_remove=[]

    for i in range(len(skel_coords)):
        for j in range(len(skel_coords)):
            if(i<j and euclidean_distance(skel_coords[i],skel_coords[j])<=pow(2,0.5) and skel_coords[i][2]>=skel_coords[j][2]):
                items_to_remove.append(skel_coords[j])    


    return list(((x[0],x[1]) for x in skel_coords if x not in items_to_remove))
  
#find the neighbours of a pixel, neartests (not diagonal) have priority
def find_neighbours(skeleton, point, excluded_points):
    neighbours = []
    point_y,point_x=point
   
    avoid_top = False
    avoid_left = False
    avoid_right = False
    avoid_botton = False
    
    #find top 
    offset_y=-1
    offset_x=0
    if(evaluate_neighbour(skeleton, point, offset_y, offset_x)):
        neighbours.append((point_y+offset_y,point_x+offset_x))
        avoid_top = True
        
    #find left
    offset_y=0
    offset_x=-1
    if(evaluate_neighbour(skeleton, point, offset_y, offset_x)):
        neighbours.append((point_y+offset_y,point_x+offset_x))
        avoid_left = True
        
    #find right
    offset_y=0
    offset_x=1
    if(evaluate_neighbour(skeleton, point, offset_y, offset_x)):
        neighbours.append((point_y+offset_y,point_x+offset_x))
        avoid_right = True
                   
    #find botton
    offset_y=1
    offset_x=0
    if(evaluate_neighbour(skeleton, point, offset_y, offset_x)):
        neighbours.append((point_y+offset_y,point_x+offset_x))
        avoid_botton = True
        
    #find botton left
    offset_y=1
    offset_x=-1
    if(evaluate_neighbour(skeleton, point, offset_y, offset_x) and not avoid_botton and not avoid_left):
        neighbours.append((point_y+offset_y,point_x+offset_x))
    
    #find botton right
    offset_y=1
    offset_x=1
    if(evaluate_neighbour(skeleton, point, offset_y, offset_x) and not avoid_botton and not avoid_right):
        neighbours.append((point_y+offset_y,point_x+offset_x))

    #find top right
    offset_y=-1
    offset_x=1
    if(evaluate_neighbour(skeleton, point, offset_y, offset_x) and not avoid_top and not avoid_right):
        neighbours.append((point_y+offset_y,point_x+offset_x))
   
        
    #find top left
    offset_y=-1
    offset_x=-1
    if(evaluate_neighbour(skeleton, point, offset_y, offset_x) and not avoid_top and not avoid_left):
        neighbours.append((point_y+offset_y,point_x+offset_x))
        
    return list((x for x in neighbours if x not in excluded_points))

def evaluate_neighbour(skeleton, point, offset_y,offset_x):
    image_width=int(skeleton.shape[1])
    image_height=int(skeleton.shape[0])
    point_y,point_x=point    
    
    if((0 <= point_y+offset_y < image_height) and (0 <= point_x+offset_x < image_width) and skeleton[point_y+offset_y,point_x+offset_x]):
        return True
    else:
        return False

#find the distantes of the joints, return a matrix of [jointA, jointB,[pixelesbetweenthem], distance in pixel]
def find_distances(skeleton, joints):    
    distances = []
           
    for j in joints:              
        #look for next points
        next_joints_points = find_neighbours(skeleton, j, [])
        
        for first_point_in_branch in next_joints_points:
            this_branch_points=[j]
            next_point = first_point_in_branch
            final_point = None
            joint_reached = False
            distance_in_pixels = 0

            while(len(find_neighbours(skeleton,next_point,this_branch_points))>0 and not joint_reached):
                old_next_point = next_point
                next_point = find_neighbours(skeleton,next_point,this_branch_points)[0]
                this_branch_points.append(old_next_point)               
                    
                if next_point in joints:
                    joint_reached = True
                
                distance_in_pixels = distance_in_pixels + euclidean_distance(old_next_point,next_point)
                final_point = next_point
               

            #not add if the oposite relation already exists       
            if(final_point is not None and not any(x[1] == j and x[0]==final_point for x in distances)):
                distances.append([j,final_point,this_branch_points,distance_in_pixels])                   
                    
    return distances

def find_meshes(final_contours):
    meshes = []

    for c in final_contours:             
        area = cv2.contourArea(c)
        meshes.append(area)

    return meshes


def paint_graph(img,graph,distance_per_pixel):
    for line in graph:
        #paint the lenght in the middle        
        for p in line[2]:
            img[p[0],p[1]] = 0

       
        #middle_y = int((line[0][0]+line[1][0])/2)
        #middle_x = int((line[0][1]+line[1][1])/2) -100 #trying to move text size to the left in order to center it
        #cv2.putText(img, "{:.1f}".format(len(line[2])),(int(middle_x), int(middle_y)), cv2.FONT_HERSHEY_SIMPLEX,1, (0, 255, 255), 3)

        #draw a circle in each node
        cv2.circle(img, (line[0][1],line[0][0]), 5, (0, 0, 0))
    

def paint_areas(img,contours):    
    
    for c in contours:              
        br = cv2.boundingRect(c)
        
        xMin=0
        yMin=0
        xMax=img.shape[0]
        yMax=img.shape[1]
    
        #if( br[0] <= xMin or br[1] <= yMin or (br[0]+br[2]) >= xMax or  (br[1]+br[3]) >= yMax):
        #        continue
            
        box = cv2.minAreaRect(c)
        box = cv2.boxPoints(box)
        box = np.array(box, dtype="int")    

        random_color = random.randint(220, 255)
        
        color = (random_color,random_color,random_color)

        cv2.drawContours(img, c, -1, color, 3)
    
        m = cv2.moments(c)
    
        divisor=m['m00']
        if(m['m00']==0):
            divisor=1
        cx = int(m['m10']/divisor)
        cy = int(m['m01']/divisor)    
           
        cv2.putText(img, "{:.1f}".format(cv2.contourArea(c)),(cx,cy ), cv2.FONT_HERSHEY_SIMPLEX,1, color, 1)

def euclidean_distance(coordinate1, coordinate2):
    return pow(pow(coordinate1[0] - coordinate2[0], 2) + pow(coordinate1[1] - coordinate2[1], 2), .5)
        
