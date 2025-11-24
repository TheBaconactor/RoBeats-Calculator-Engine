-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:32 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local s_UserInputService_0 = game:GetService("UserInputService")
local s_GuiService_0 = game:GetService("GuiService")
local v_u_1 = require(script.Parent)
local v2 = {}
while not s_Players_0.LocalPlayer do
    wait()
end;
local v_u_3 = nil
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = Vector3.new(0, 0, 0)
local v_u_9 = false
v2.set_functionality_enabled = function(_, p10) --[[ Name: set_functionality_enabled ]] --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_3, (ref 3): v_u_5 ]]
    v_u_9 = p10
    v_u_3.Visible = p10
    if v_u_5 and (p10 == false and v_u_3.Visible == true) then
        v_u_5()
    end;
end;
v2.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 43 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_3 ]]
    if v_u_9 == true then
        if v_u_3 then
            v_u_3.Visible = true
        end;
    else
        v_u_3.Visible = false
    end;
end;
v2.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 54 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_3, (ref 3): v_u_5 ]]
    if v_u_9 == true then
        v_u_3.Visible = true
    else
        if v_u_3 then
            v_u_3.Visible = false
        end;
        v_u_5()
    end;
end;
v2.Create = function(_, p11) --[[ Name: Create ]] --[[ Line: 66 ]]
    --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_7, (copy 4): v_u_1, (ref 5): v_u_8, (ref 6): v_u_4, (copy 7): s_UserInputService_0, (ref 8): v_u_5, (copy 9): s_GuiService_0 ]]
    if v_u_3 then
        v_u_3:Destroy()
        v_u_3 = nil
        if v_u_6 then
            v_u_6:disconnect()
            v_u_6 = nil
        end;
        if v_u_7 then
            v_u_7:disconnect()
            v_u_7 = nil
        end;
    end;
    local v12 = p11.AbsoluteSize.y <= 500
    local v_u_13 = v12 and 70 or 120
    local v_u_14 = v12 and UDim2.new(0, v_u_13 / 2 - 10, 1, -v_u_13 - 20) or UDim2.new(0, v_u_13 / 2, 1, -v_u_13 * 1.75)
    v_u_3 = Instance.new("Frame")
    v_u_3.Name = "ThumbstickFrame"
    v_u_3.Active = true
    v_u_3.Visible = false
    v_u_3.Size = UDim2.new(0, v_u_13, 0, v_u_13)
    v_u_3.Position = v_u_14
    v_u_3.BackgroundTransparency = 1
    local l_ImageLabel_0 = Instance.new("ImageLabel")
    l_ImageLabel_0.Name = "OuterImage"
    l_ImageLabel_0.Image = "rbxasset://textures/ui/TouchControlsSheet.png"
    l_ImageLabel_0.ImageRectOffset = Vector2.new()
    l_ImageLabel_0.ImageRectSize = Vector2.new(220, 220)
    l_ImageLabel_0.BackgroundTransparency = 1
    l_ImageLabel_0.Size = UDim2.new(0, v_u_13, 0, v_u_13)
    l_ImageLabel_0.Position = UDim2.new(0, 0, 0, 0)
    l_ImageLabel_0.Parent = v_u_3
    StickImage = Instance.new("ImageLabel")
    StickImage.Name = "StickImage"
    StickImage.Image = "rbxasset://textures/ui/TouchControlsSheet.png"
    StickImage.ImageRectOffset = Vector2.new(220, 0)
    StickImage.ImageRectSize = Vector2.new(111, 111)
    StickImage.BackgroundTransparency = 1
    StickImage.Size = UDim2.new(0, v_u_13 / 2, 0, v_u_13 / 2)
    StickImage.Position = UDim2.new(0, v_u_13 / 2 - v_u_13 / 4, 0, v_u_13 / 2 - v_u_13 / 4)
    StickImage.ZIndex = 2
    StickImage.Parent = v_u_3
    local v_u_15 = nil
    local function _(p16) --[[ Name: doMove ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (copy 3): v_u_13 ]]
        v_u_1:AddToPlayerMovement(-v_u_8)
        v_u_8 = p16 / (v_u_13 / 2)
        local l_magnitude_0 = v_u_8.magnitude
        if l_magnitude_0 < 0.05 then
            v_u_8 = Vector3.new()
        else
            v_u_8 = v_u_8.unit * ((l_magnitude_0 - 0.05) / 0.95)
            v_u_8 = Vector3.new(v_u_8.x, 0, v_u_8.y)
        end;
        v_u_1:AddToPlayerMovement(v_u_8)
    end;
    local function f_moveStick(p17) --[[ Name: moveStick ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_3 ]]
        local v18 = Vector2.new(p17.x - v_u_15.x, p17.y - v_u_15.y)
        local v19 = v18.unit * math.min(v18.magnitude, v_u_3.AbsoluteSize.x / 2)
        StickImage.Position = UDim2.new(0, v19.x + StickImage.AbsoluteSize.x / 2, 0, v19.y + StickImage.AbsoluteSize.y / 2)
    end;
    v_u_3.InputBegan:connect(function(p20) --[[ Line: 152 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_3, (ref 3): v_u_15 ]]
        if not v_u_4 and p20.UserInputType == Enum.UserInputType.Touch then
            v_u_4 = p20
            v_u_3.Position = UDim2.new(0, p20.Position.x - v_u_3.Size.X.Offset / 2, 0, p20.Position.y - v_u_3.Size.Y.Offset / 2)
            v_u_15 = Vector2.new(v_u_3.AbsolutePosition.x + v_u_3.AbsoluteSize.x / 2, v_u_3.AbsolutePosition.y + v_u_3.AbsoluteSize.y / 2)
        end;
    end)
    v_u_6 = s_UserInputService_0.TouchMoved:connect(function(p21, _) --[[ Line: 163 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_15, (ref 3): v_u_3, (ref 4): v_u_1, (ref 5): v_u_8, (copy 6): v_u_13, (copy 7): f_moveStick ]]
        if p21 == v_u_4 then
            v_u_15 = Vector2.new(v_u_3.AbsolutePosition.x + v_u_3.AbsoluteSize.x / 2, v_u_3.AbsolutePosition.y + v_u_3.AbsoluteSize.y / 2)
            local v22 = Vector2.new(p21.Position.x - v_u_15.x, p21.Position.y - v_u_15.y)
            v_u_1:AddToPlayerMovement(-v_u_8)
            v_u_8 = v22 / (v_u_13 / 2)
            local l_magnitude_1 = v_u_8.magnitude
            if l_magnitude_1 < 0.05 then
                v_u_8 = Vector3.new()
            else
                v_u_8 = v_u_8.unit * ((l_magnitude_1 - 0.05) / 0.95)
                v_u_8 = Vector3.new(v_u_8.x, 0, v_u_8.y)
            end;
            v_u_1:AddToPlayerMovement(v_u_8)
            f_moveStick(p21.Position)
        end;
    end)
    v_u_5 = function() --[[ Line: 173 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_14, (copy 3): v_u_13, (ref 4): v_u_4, (ref 5): v_u_1, (ref 6): v_u_8 ]]
        v_u_3.Position = v_u_14
        StickImage.Position = UDim2.new(0, v_u_3.Size.X.Offset / 2 - v_u_13 / 4, 0, v_u_3.Size.Y.Offset / 2 - v_u_13 / 4)
        v_u_4 = nil
        v_u_1:AddToPlayerMovement(-v_u_8)
        v_u_8 = Vector3.new(0, 0, 0)
        v_u_1:SetIsJumping(false)
    end
    v_u_7 = s_UserInputService_0.TouchEnded:connect(function(p23, _) --[[ Line: 183 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5 ]]
        if p23 == v_u_4 then
            v_u_5()
        end;
    end)
    s_GuiService_0.MenuOpened:connect(function() --[[ Line: 189 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5 ]]
        if v_u_4 then
            v_u_5()
        end;
    end)
    v_u_3.Parent = p11
end;
return v2;
