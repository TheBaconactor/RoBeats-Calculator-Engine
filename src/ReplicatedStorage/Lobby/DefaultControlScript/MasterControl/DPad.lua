-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local s_GuiService_0 = game:GetService("GuiService")
local v_u_1 = require(script.Parent)
local v2 = {}
while not s_Players_0.LocalPlayer do
    wait()
end;
local v_u_3 = nil
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = {
    Vector3.new(1, 0, 0),
    (Vector3.new(1, 0, 1)).unit,
    Vector3.new(0, 0, 1),
    (Vector3.new(-1, 0, 1)).unit,
    Vector3.new(-1, 0, 0),
    (Vector3.new(-1, 0, -1)).unit,
    Vector3.new(0, 0, -1),
    (Vector3.new(1, 0, -1)).unit
}
local l_atan2_0 = math.atan2
local l_floor_0 = math.floor
local function _(p7, p8, p9, p10, p11) --[[ Name: createArrowLabel ]] --[[ Line: 43 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    local l_ImageLabel_0 = Instance.new("ImageLabel")
    l_ImageLabel_0.Name = p7
    l_ImageLabel_0.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_0.ImageRectOffset = p10
    l_ImageLabel_0.ImageRectSize = p11
    l_ImageLabel_0.BackgroundTransparency = 1
    l_ImageLabel_0.Size = p9
    l_ImageLabel_0.Position = p8
    l_ImageLabel_0.Parent = v_u_3
    return l_ImageLabel_0;
end;
local function _() --[[ Name: getCenterPosition ]] --[[ Line: 57 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    return Vector2.new(v_u_3.AbsolutePosition.x + v_u_3.AbsoluteSize.x / 2, v_u_3.AbsolutePosition.y + v_u_3.AbsoluteSize.y / 2);
end;
v2.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 62 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    v_u_3.Visible = true
end;
v2.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 66 ]]
    --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_5 ]]
    v_u_3.Visible = false
    v_u_5()
end;
v2.Create = function(_, p12) --[[ Name: Create ]] --[[ Line: 71 ]]
    --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_1, (copy 3): l_atan2_0, (copy 4): l_floor_0, (copy 5): v_u_6, (ref 6): v_u_4, (ref 7): v_u_5, (copy 8): s_GuiService_0 ]]
    if v_u_3 then
        v_u_3:Destroy()
        v_u_3 = nil
    end;
    local v13 = UDim2.new(0, 10, 1, -230)
    v_u_3 = Instance.new("Frame")
    v_u_3.Name = "DPadFrame"
    v_u_3.Active = true
    v_u_3.Visible = false
    v_u_3.Size = UDim2.new(0, 192, 0, 192)
    v_u_3.Position = v13
    v_u_3.BackgroundTransparency = 1
    local v14 = UDim2.new(0, 23, 0, 23)
    local v15 = UDim2.new(0, 64, 0, 64)
    local v16 = Vector2.new(46, 46)
    local v17 = Vector2.new(128, 128)
    local v18 = UDim2.new(0.5, -32, 1, -64)
    local v19 = Vector2.new(0, 0)
    local l_ImageLabel_1 = Instance.new("ImageLabel")
    l_ImageLabel_1.Name = "BackButton"
    l_ImageLabel_1.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_1.ImageRectOffset = v19
    l_ImageLabel_1.ImageRectSize = v17
    l_ImageLabel_1.BackgroundTransparency = 1
    l_ImageLabel_1.Size = v15
    l_ImageLabel_1.Position = v18
    l_ImageLabel_1.Parent = v_u_3
    local v20 = UDim2.new(0.5, -32, 0, 0)
    local v21 = Vector2.new(0, 258)
    local l_ImageLabel_2 = Instance.new("ImageLabel")
    l_ImageLabel_2.Name = "ForwardButton"
    l_ImageLabel_2.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_2.ImageRectOffset = v21
    l_ImageLabel_2.ImageRectSize = v17
    l_ImageLabel_2.BackgroundTransparency = 1
    l_ImageLabel_2.Size = v15
    l_ImageLabel_2.Position = v20
    l_ImageLabel_2.Parent = v_u_3
    local v22 = UDim2.new(0, 0, 0.5, -32)
    local v23 = Vector2.new(129, 129)
    local l_ImageLabel_3 = Instance.new("ImageLabel")
    l_ImageLabel_3.Name = "LeftButton"
    l_ImageLabel_3.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_3.ImageRectOffset = v23
    l_ImageLabel_3.ImageRectSize = v17
    l_ImageLabel_3.BackgroundTransparency = 1
    l_ImageLabel_3.Size = v15
    l_ImageLabel_3.Position = v22
    l_ImageLabel_3.Parent = v_u_3
    local v24 = UDim2.new(1, -64, 0.5, -32)
    local v25 = Vector2.new(0, 129)
    local l_ImageLabel_4 = Instance.new("ImageLabel")
    l_ImageLabel_4.Name = "RightButton"
    l_ImageLabel_4.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_4.ImageRectOffset = v25
    l_ImageLabel_4.ImageRectSize = v17
    l_ImageLabel_4.BackgroundTransparency = 1
    l_ImageLabel_4.Size = v15
    l_ImageLabel_4.Position = v24
    l_ImageLabel_4.Parent = v_u_3
    local v26 = UDim2.new(0.5, -32, 0.5, -32)
    local v27 = Vector2.new(129, 0)
    local l_ImageLabel_5 = Instance.new("ImageLabel")
    l_ImageLabel_5.Name = "JumpButton"
    l_ImageLabel_5.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_5.ImageRectOffset = v27
    l_ImageLabel_5.ImageRectSize = v17
    l_ImageLabel_5.BackgroundTransparency = 1
    l_ImageLabel_5.Size = v15
    l_ImageLabel_5.Position = v26
    l_ImageLabel_5.Parent = v_u_3
    local v_u_28 = l_ImageLabel_5
    local v29 = UDim2.new(0, 35, 0, 35)
    local v30 = Vector2.new(129, 258)
    local l_ImageLabel_6 = Instance.new("ImageLabel")
    l_ImageLabel_6.Name = "ForwardLeftButton"
    l_ImageLabel_6.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_6.ImageRectOffset = v30
    l_ImageLabel_6.ImageRectSize = v16
    l_ImageLabel_6.BackgroundTransparency = 1
    l_ImageLabel_6.Size = v14
    l_ImageLabel_6.Position = v29
    l_ImageLabel_6.Parent = v_u_3
    local v31 = UDim2.new(1, -55, 0, 35)
    local v32 = Vector2.new(176, 258)
    local l_ImageLabel_7 = Instance.new("ImageLabel")
    l_ImageLabel_7.Name = "ForwardRightButton"
    l_ImageLabel_7.Image = "rbxasset://textures/ui/DPadSheet.png"
    l_ImageLabel_7.ImageRectOffset = v32
    l_ImageLabel_7.ImageRectSize = v16
    l_ImageLabel_7.BackgroundTransparency = 1
    l_ImageLabel_7.Size = v14
    l_ImageLabel_7.Position = v31
    l_ImageLabel_7.Parent = v_u_3
    l_ImageLabel_6.Visible = false
    l_ImageLabel_7.Visible = false
    v_u_28.InputBegan:connect(function(_) --[[ Line: 102 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        v_u_1:DoJump()
    end)
    local v_u_33 = Vector3.new(0, 0, 0)
    local function f_normalizeDirection(p34) --[[ Name: normalizeDirection ]] --[[ Line: 107 ]]
        --[[ Upvalues: (copy 1): v_u_28, (ref 2): v_u_3, (ref 3): l_atan2_0, (ref 4): l_floor_0, (ref 5): v_u_33, (ref 6): v_u_6, (copy 7): l_ImageLabel_6, (copy 8): l_ImageLabel_7 ]]
        local v35 = v_u_28.AbsoluteSize.x / 2
        local v36 = Vector2.new(v_u_3.AbsolutePosition.x + v_u_3.AbsoluteSize.x / 2, v_u_3.AbsolutePosition.y + v_u_3.AbsoluteSize.y / 2)
        local v37 = Vector2.new(p34.x - v36.x, p34.y - v36.y)
        if v35 < v37.magnitude then
            v_u_33 = v_u_6[l_floor_0(l_atan2_0(v37.y, v37.x) * 8 / 6.283185307179586 + 8.5) % 8 + 1]
        end;
        if not l_ImageLabel_6.Visible and v_u_33 == v_u_6[7] then
            l_ImageLabel_6.Visible = true
            l_ImageLabel_7.Visible = true
        end;
    end;
    v_u_3.InputBegan:connect(function(p38) --[[ Line: 124 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (ref 3): v_u_33, (copy 4): f_normalizeDirection ]]
        if not v_u_4 and p38.UserInputType == Enum.UserInputType.Touch then
            v_u_1:AddToPlayerMovement(-v_u_33)
            v_u_4 = p38
            f_normalizeDirection(v_u_4.Position)
            v_u_1:AddToPlayerMovement(v_u_33)
        end;
    end)
    v_u_3.InputChanged:connect(function(p39) --[[ Line: 137 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (ref 3): v_u_33, (copy 4): f_normalizeDirection ]]
        if p39 == v_u_4 then
            v_u_1:AddToPlayerMovement(-v_u_33)
            f_normalizeDirection(v_u_4.Position)
            v_u_1:AddToPlayerMovement(v_u_33)
            v_u_1:SetIsJumping(false)
        end;
    end)
    v_u_5 = function() --[[ Line: 146 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): l_ImageLabel_6, (copy 3): l_ImageLabel_7, (ref 4): v_u_1, (ref 5): v_u_33 ]]
        v_u_4 = nil
        l_ImageLabel_6.Visible = false
        l_ImageLabel_7.Visible = false
        v_u_1:AddToPlayerMovement(-v_u_33)
        v_u_33 = Vector3.new(0, 0, 0)
    end
    v_u_3.InputEnded:connect(function(p40) --[[ Line: 155 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5 ]]
        if p40 == v_u_4 then
            v_u_5()
        end;
    end)
    s_GuiService_0.MenuOpened:connect(function() --[[ Line: 161 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5 ]]
        if v_u_4 then
            v_u_5()
        end;
    end)
    v_u_3.Parent = p12
end;
return v2;
