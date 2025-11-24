-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:24 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_5 = require(game.ReplicatedStorage.Shared.LVector3)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_7 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_51 = {
    ["_new"] = function(_, p_u_8, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: _new ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_5, (copy 7): v_u_3 ]]
        local v19 = v_u_1:EffectBase()
        v19.rebind = function(_, p20, p21, p22, p23, p24, p25, p26, p27, p28, p29, p30) --[[ Name: rebind ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): p_u_8, (ref 2): p_u_9, (ref 3): p_u_10, (ref 4): p_u_11, (ref 5): p_u_12, (ref 6): p_u_13, (ref 7): p_u_14, (ref 8): p_u_15, (ref 9): p_u_16, (ref 10): p_u_17, (ref 11): p_u_18 ]]
            p_u_8 = p20
            p_u_9 = p21
            p_u_10 = p22
            p_u_11 = p23
            p_u_12 = p24
            p_u_13 = p25
            p_u_14 = p26
            p_u_15 = p27
            p_u_16 = p28
            p_u_17 = p29
            p_u_18 = p30
        end;
        local v_u_31 = nil
        local v_u_32 = 0
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = nil
        local v_u_40 = nil
        v19.cons = function(p41) --[[ Name: cons ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_31, (ref 3): p_u_8, (ref 4): v_u_2, (ref 5): v_u_33, (ref 6): v_u_34, (ref 7): v_u_35, (ref 8): v_u_36, (ref 9): v_u_37, (ref 10): v_u_38, (ref 11): v_u_39, (ref 12): v_u_40, (ref 13): p_u_10, (ref 14): v_u_4, (ref 15): p_u_11, (ref 16): p_u_13, (ref 17): p_u_14, (ref 18): v_u_6, (ref 19): p_u_12, (ref 20): v_u_7, (ref 21): p_u_15, (ref 22): p_u_16, (ref 23): p_u_17, (ref 24): p_u_18, (ref 25): p_u_9 ]]
            v_u_32 = 0
            v_u_31 = p_u_8._object_pool:depool("NoteResultPopupEffectV2")
            if v_u_31 == nil then
                v_u_31 = game.ReplicatedStorage.ElementProtos.NoteResultPopupEffectV2:Clone()
            end;
            v_u_31.Name = v_u_2:gen_name(v_u_31.Name)
            v_u_33 = v_u_31.Panel.SurfaceGui.Frame
            v_u_34 = v_u_33.ImageLabel
            v_u_35 = v_u_33.PointsDisplay
            v_u_36 = v_u_33.MultDisplay
            v_u_37 = v_u_33.ColorIconPrimary
            v_u_38 = v_u_33.ColorIconSecondary
            v_u_39 = v_u_33.ColorTextPrimary
            v_u_40 = v_u_33.ColorTextSecondary
            if p_u_10 == v_u_4.NoteResult_Miss then
                v_u_34.Image = v_u_2:get_hitword_miss_assetid()
                v_u_35.Text = ""
            elseif p_u_10 == v_u_4.NoteResult_Okay then
                v_u_34.Image = v_u_2:get_hitword_okay_assetid()
                v_u_35.Text = "+" .. p_u_11
                v_u_35.TextColor3 = v_u_2:color3(239, 248, 143)
            elseif p_u_10 == v_u_4.NoteResult_Great then
                v_u_34.Image = v_u_2:get_hitword_great_assetid()
                v_u_35.Text = "+" .. p_u_11
                v_u_35.TextColor3 = v_u_2:color3(130, 238, 123)
            else
                v_u_34.Image = v_u_2:get_hitword_perfect_assetid()
                v_u_35.Text = "+" .. p_u_11
                v_u_35.TextColor3 = v_u_2:color3(152, 247, 253)
            end;
            if p_u_13 == true then
                v_u_36.TextColor3 = Color3.fromRGB(33, 255, 227)
            elseif p_u_14 == v_u_6.ComboMultiplierThreshold.Threshold1 then
                v_u_36.TextColor3 = Color3.fromRGB(178, 190, 255)
            elseif p_u_14 == v_u_6.ComboMultiplierThreshold.Threshold2 then
                v_u_36.TextColor3 = Color3.fromRGB(153, 133, 255)
            elseif p_u_14 == v_u_6.ComboMultiplierThreshold.Threshold3 then
                v_u_36.TextColor3 = Color3.fromRGB(175, 130, 232)
            else
                v_u_36.TextColor3 = Color3.fromRGB(221, 118, 250)
            end;
            if p_u_10 == v_u_4.NoteResult_Miss then
                v_u_36.Text = ""
                v_u_37.Visible = false
                v_u_39.Text = ""
                v_u_38.Visible = false
                v_u_40.Text = ""
            else
                v_u_36.Text = string.format("x%.2f", p_u_12)
                v_u_37.Visible = true
                v_u_37.Image = v_u_7:color_to_iconimage(p_u_15)
                v_u_39.Text = tostring(p_u_16)
                if p_u_16 > 0 then
                    v_u_39.TextColor3 = v_u_7:color_to_color3(p_u_15)
                else
                    v_u_39.TextColor3 = Color3.fromRGB(170, 170, 170)
                end;
                if p_u_17 == nil then
                    v_u_38.Visible = false
                    v_u_40.Text = ""
                else
                    v_u_38.Visible = true
                    v_u_38.Image = v_u_7:color_to_iconimage(p_u_17)
                    v_u_40.Text = tostring(p_u_18)
                    if p_u_18 > 0 then
                        v_u_40.TextColor3 = v_u_7:color_to_color3(p_u_17)
                    else
                        v_u_40.TextColor3 = Color3.fromRGB(170, 170, 170)
                    end;
                end;
            end;
            v_u_31:SetPrimaryPartCFrame(v_u_2:lookat_camera_cframe(p_u_9, p_u_8._spui))
            p41:update_visual()
        end;
        v19.get_anim_t = function(_) --[[ Name: get_anim_t ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            return v_u_32;
        end;
        v19.set_anim_t = function(_, p42) --[[ Name: set_anim_t ]] --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            v_u_32 = p42
        end;
        local v_u_43 = v_u_5.new(0, 0.65)
        local v_u_44 = v_u_5.new(1, 0)
        v19.update_visual = function(_) --[[ Name: update_visual ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_3, (ref 3): v_u_32, (copy 4): v_u_43, (copy 5): v_u_44, (ref 6): v_u_2, (ref 7): v_u_34, (ref 8): v_u_35, (ref 9): v_u_36, (ref 10): v_u_39, (ref 11): v_u_40, (ref 12): v_u_37, (ref 13): v_u_38 ]]
            v_u_33.Position = UDim2.new(0, 0, 0, v_u_3:Lerp(125, 190, v_u_32))
            local v45 = v_u_2:tra((v_u_3:YForPointOf2PtLine(v_u_43, v_u_44, v_u_32)))
            v_u_34.ImageTransparency = v45
            v_u_35.TextTransparency = v45
            local v46 = v_u_2:tra(v_u_2:clamp(v_u_3:BezierPt2ForT(0, -1, 0.75, 0.25, 0.75, 0.25, 1, 0.75, 1 - v_u_32).Y, 0, 1))
            v_u_35.TextStrokeTransparency = v46
            v_u_36.TextTransparency = v45
            v_u_36.TextStrokeTransparency = v46
            v_u_39.TextTransparency = v45
            v_u_39.TextStrokeTransparency = v46
            v_u_40.TextTransparency = v45
            v_u_40.TextStrokeTransparency = v46
            v_u_37.ImageTransparency = v46
            v_u_38.ImageTransparency = v46
        end;
        v19.add_to_parent = function(_, p47, _) --[[ Name: add_to_parent ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            v_u_31.Parent = p47
        end;
        v19.update = function(p48, p49, _) --[[ Name: update ]] --[[ Line: 202 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_3 ]]
            v_u_32 = v_u_32 + v_u_3:SecondsToTick(0.55) * p49
            p48:update_visual()
        end;
        v19.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 208 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            return v_u_32 >= 1;
        end;
        v19.do_remove = function(p50, _) --[[ Name: do_remove ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): p_u_8, (ref 2): v_u_31 ]]
            p_u_8._object_pool:repool("NoteResultPopupEffectV2", v_u_31)
            p_u_8._lua_pool:repool("NoteResultPopupEffectV2", p50)
        end;
        return v19;
    end
}
local function _() --[[ Name: pool_str ]] --[[ Line: 12 ]]
    return "NoteResultPopupEffectV2";
end;
v_u_51.new = function(_, p52, p53, p54, p55, p56, p57, p58, p59, p60, p61, p62) --[[ Name: new ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_51 ]]
    local v63 = p52._lua_pool:depool("NoteResultPopupEffectV2")
    if v63 == nil then
        local v64 = v_u_51:_new(p52, p53, p54, p55, p56, p57, p58, p59, p60, p61, p62)
        v64:cons()
        return v64;
    else
        v63:rebind(p52, p53, p54, p55, p56, p57, p58, p59, p60, p61, p62)
        v63:cons()
        return v63;
    end;
end;
v_u_51.prepool = function(_, p65) --[[ Name: prepool ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_51 ]]
    p65._lua_pool:repool("NoteResultPopupEffectV2", v_u_51:_new())
end;
return v_u_51;
