import Assets


class Button:
    def __init__(self, image, x, y):  # defines button assets and positions rect
        self.image = image
        self.rect = self.image.get_rect()
        self.pos = (x, y)
        self.rect.topleft = self.pos

    def draw(self, surface):  # draws button to screen at position of rect
        surface.blit(self.image, self.pos)

    def check_clicked(self, pos):  # returns boolean if mouse click is over rect
        return self.rect.collidepoint(pos)


class CheckBox:
    def __init__(self, x, y):
        self.image = Assets.assets['Check Box 1']  # defines Checkbox initial filled asset
        self.rect = self.image.get_rect()
        self.pos = (x, y)
        self.rect.topleft = self.pos
        self.value = True  # value reprented by checkbox is initially filled/true

    def draw(self, surface):
        surface.blit(self.image, self.pos)

    def check_clicked(self, pos):
        if self.rect.collidepoint(pos):  # returns boolean if clicked
            self.value = not self.value
            self.image = Assets.assets[f'Check Box {int(self.value)}']  # asset is updated depending on value
            return True
        return False


class Slider:
    def __init__(self, x, y):
        self.bar_image = Assets.assets['Bar']  # loads bar and slider assets
        self.slider_image = Assets.assets['Slider']

        self.value = 1.0  # initial maximum value of slider

        self.bar_rect = self.bar_image.get_rect()  # positions slider and bar on screen
        self.bar_rect.topleft = (x, y)
        self.slider_rect = self.slider_image.get_rect()
        self.slider_rect.midleft = (self.bar_rect.left+self.bar_rect.width*self.value - self.slider_rect.width,
                                    self.bar_rect.centery)  # positions slider on bar with initial value

    def draw(self, surface):  # draws bar and slider at defined positions
        surface.blit(self.bar_image, self.bar_rect)
        surface.blit(self.slider_image, self.slider_rect)

    def check_clicked(self, pos):  # returns boolean value if bar was clicked and updates value and slider position
        if clicked := self.bar_rect.collidepoint(pos):
            bar_min = self.bar_rect.left
            bar_max = self.bar_rect.right-self.slider_rect.width
            self.slider_rect.left = min(max(bar_min, pos[0]), bar_max)  # sets new slider position with bounds
            self.value = (min(max(bar_min, pos[0]), bar_max)-bar_min)/(self.bar_rect.width-self.slider_rect.width)  # sets value with bounds
        return clicked

    def drag(self, pos):  # updates slider position depending on  mouse position anywhere on screen
        bar_min = self.bar_rect.left
        bar_max = self.bar_rect.right-self.slider_rect.width
        self.slider_rect.left = min(max(bar_min, pos[0]), bar_max)
        self.value = (min(max(bar_min, pos[0]), bar_max)-bar_min)/(self.bar_rect.width-self.slider_rect.width)
