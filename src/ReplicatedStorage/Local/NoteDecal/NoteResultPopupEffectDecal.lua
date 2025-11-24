-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:28 PM
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
local v_u_56 = {
    ["_new"] = function(_, p_u_8, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: _new ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_5, (copy 7): v_u_3 ]]
        local v19 = v_u_1:EffectBase()
        v19.rebind = function(_, p20, p21, p22, p23, p24, p25, p26, p27, p28, p29, p30) --[[ Name: rebind ]] --[[ Line: 46 ]]
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
        local v_u_32 = nil
        local v_u_33 = 0
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = nil
        local v_u_40 = nil
        local v_u_41 = nil
        local v_u_42 = nil
        local v_u_43 = nil
        local v_u_44 = nil
        v19.cons = function(p45) --[[ Name: cons ]] --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): p_u_8, (ref 3): v_u_33, (ref 4): v_u_32, (ref 5): v_u_2, (ref 6): v_u_34, (ref 7): v_u_37, (ref 8): v_u_35, (ref 9): v_u_36, (ref 10): v_u_38, (ref 11): v_u_39, (ref 12): v_u_40, (ref 13): v_u_41, (ref 14): v_u_42, (ref 15): v_u_43, (ref 16): v_u_44, (ref 17): p_u_10, (ref 18): v_u_4, (ref 19): p_u_11, (ref 20): p_u_13, (ref 21): p_u_14, (ref 22): v_u_6, (ref 23): p_u_12, (ref 24): v_u_7, (ref 25): p_u_15, (ref 26): p_u_16, (ref 27): p_u_17, (ref 28): p_u_18, (ref 29): p_u_9 ]]
            v_u_31 = p_u_8._ui_manager:get_decal_ui_manager()
            v_u_33 = 0
            v_u_32 = p_u_8._object_pool:depool("NoteResultPopupEffectDecal")
            if v_u_32 == nil then
                v_u_32 = game.ReplicatedStorage.ElementProtos.NoteResultPopupEffectDecal:Clone()
            end;
            v_u_32.Name = v_u_2:gen_name(v_u_32.Name)
            v_u_34 = v_u_32.Panel.SurfaceGui
            v_u_37 = v_u_34.Frame
            v_u_35 = v_u_37.UIScale
            v_u_36 = v_u_37.Size.X.Offset
            v_u_37.Parent = v_u_31:get_screengui()
            v_u_38 = v_u_37.ImageLabel
            v_u_39 = v_u_37.PointsDisplay
            v_u_40 = v_u_37.MultDisplay
            v_u_41 = v_u_37.ColorIconPrimary
            v_u_42 = v_u_37.ColorIconSecondary
            v_u_43 = v_u_37.ColorTextPrimary
            v_u_44 = v_u_37.ColorTextSecondary
            if p_u_10 == v_u_4.NoteResult_Miss then
                v_u_38.Image = v_u_2:get_hitword_miss_assetid()
                v_u_39.Text = ""
            elseif p_u_10 == v_u_4.NoteResult_Okay then
                v_u_38.Image = v_u_2:get_hitword_okay_assetid()
                v_u_39.Text = "+" .. p_u_11
                v_u_39.TextColor3 = v_u_2:color3(239, 248, 143)
            elseif p_u_10 == v_u_4.NoteResult_Great then
                v_u_38.Image = v_u_2:get_hitword_great_assetid()
                v_u_39.Text = "+" .. p_u_11
                v_u_39.TextColor3 = v_u_2:color3(130, 238, 123)
            else
                v_u_38.Image = v_u_2:get_hitword_perfect_assetid()
                v_u_39.Text = "+" .. p_u_11
                v_u_39.TextColor3 = v_u_2:color3(152, 247, 253)
            end;
            if p_u_13 == true then
                v_u_40.TextColor3 = Color3.fromRGB(33, 255, 227)
            elseif p_u_14 == v_u_6.ComboMultiplierThreshold.Threshold1 then
                v_u_40.TextColor3 = Color3.fromRGB(178, 190, 255)
            elseif p_u_14 == v_u_6.ComboMultiplierThreshold.Threshold2 then
                v_u_40.TextColor3 = Color3.fromRGB(153, 133, 255)
            elseif p_u_14 == v_u_6.ComboMultiplierThreshold.Threshold3 then
                v_u_40.TextColor3 = Color3.fromRGB(175, 130, 232)
            else
                v_u_40.TextColor3 = Color3.fromRGB(221, 118, 250)
            end;
            if p_u_10 == v_u_4.NoteResult_Miss then
                v_u_40.Text = ""
                v_u_41.Visible = false
                v_u_43.Text = ""
                v_u_42.Visible = false
                v_u_44.Text = ""
            else
                v_u_40.Text = string.format("x%.2f", p_u_12)
                v_u_41.Visible = true
                v_u_41.Image = v_u_7:color_to_iconimage(p_u_15)
                v_u_43.Text = tostring(p_u_16)
                if p_u_16 > 0 then
                    v_u_43.TextColor3 = v_u_7:color_to_color3(p_u_15)
                else
                    v_u_43.TextColor3 = Color3.fromRGB(170, 170, 170)
                end;
                if p_u_17 == nil then
                    v_u_42.Visible = false
                    v_u_44.Text = ""
                else
                    v_u_42.Visible = true
                    v_u_42.Image = v_u_7:color_to_iconimage(p_u_17)
                    v_u_44.Text = tostring(p_u_18)
                    if p_u_18 > 0 then
                        v_u_44.TextColor3 = v_u_7:color_to_color3(p_u_17)
                    else
                        v_u_44.TextColor3 = Color3.fromRGB(170, 170, 170)
                    end;
                end;
            end;
            v_u_37.Position = UDim2.new(0, p_u_9.X, 0, p_u_9.Y)
            p45:update_visual()
        end;
        v19.get_anim_t = function(_) --[[ Name: get_anim_t ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            return v_u_33;
        end;
        v19.set_anim_t = function(_, p46) --[[ Name: set_anim_t ]] --[[ Line: 162 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            v_u_33 = p46
        end;
        local v_u_47 = v_u_5.new(0, 0.65)
        local v_u_48 = v_u_5.new(1, 0)
        v19.update_visual = function(_) --[[ Name: update_visual ]] --[[ Line: 166 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_36, (ref 3): v_u_35, (ref 4): v_u_37, (ref 5): p_u_9, (ref 6): v_u_3, (ref 7): v_u_33, (copy 8): v_u_47, (copy 9): v_u_48, (ref 10): v_u_2, (ref 11): v_u_38, (ref 12): v_u_39, (ref 13): v_u_40, (ref 14): v_u_43, (ref 15): v_u_44, (ref 16): v_u_41, (ref 17): v_u_42 ]]
            local v49, _ = v_u_31:get_track_size_and_position()
            local v50 = v49._x / v_u_36
            v_u_35.Scale = v50 * 2
            v_u_37.Position = UDim2.new(0, p_u_9.X, 0, p_u_9.Y + v_u_3:Lerp(0, v50 * 150, v_u_33))
            local v51 = v_u_2:tra((v_u_3:YForPointOf2PtLine(v_u_47, v_u_48, v_u_33)))
            v_u_38.ImageTransparency = v51
            v_u_39.TextTransparency = v51
            local v52 = v_u_2:tra(v_u_2:clamp(v_u_3:BezierPt2ForT(0, -1, 0.75, 0.25, 0.75, 0.25, 1, 0.75, 1 - v_u_33).Y, 0, 1))
            v_u_39.TextStrokeTransparency = v52
            v_u_40.TextTransparency = v51
            v_u_40.TextStrokeTransparency = v52
            v_u_43.TextTransparency = v51
            v_u_43.TextStrokeTransparency = v52
            v_u_44.TextTransparency = v51
            v_u_44.TextStrokeTransparency = v52
            v_u_41.ImageTransparency = v52
            v_u_42.ImageTransparency = v52
        end;
        v19.add_to_parent = function(_, _, _) end;
        v19.update = function(p53, p54, _) --[[ Name: update ]] --[[ Line: 214 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_3 ]]
            v_u_33 = v_u_33 + v_u_3:SecondsToTick(0.55) * p54
            p53:update_visual()
        end;
        v19.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            return v_u_33 >= 1;
        end;
        v19.do_remove = function(p55, _) --[[ Name: do_remove ]] --[[ Line: 223 ]]
            --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_34, (ref 3): p_u_8, (ref 4): v_u_32 ]]
            v_u_37.Parent = v_u_34
            p_u_8._object_pool:repool("NoteResultPopupEffectDecal", v_u_32)
            p_u_8._lua_pool:repool("NoteResultPopupEffectDecal", p55)
        end;
        return v19;
    end
}
local function _() --[[ Name: pool_str ]] --[[ Line: 12 ]]
    return "NoteResultPopupEffectDecal";
end;
v_u_56.new = function(_, p57, p58, p59, p60, p61, p62, p63, p64, p65, p66, p67) --[[ Name: new ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_56 ]]
    local v68 = p57._lua_pool:depool("NoteResultPopupEffectDecal")
    if v68 == nil then
        local v69 = v_u_56:_new(p57, p58, p59, p60, p61, p62, p63, p64, p65, p66, p67)
        v69:cons()
        return v69;
    else
        v68:rebind(p57, p58, p59, p60, p61, p62, p63, p64, p65, p66, p67)
        v68:cons()
        return v68;
    end;
end;
v_u_56.prepool = function(_, p70) --[[ Name: prepool ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_56 ]]
    p70._lua_pool:repool("NoteResultPopupEffectDecal", v_u_56:_new())
end;
return v_u_56;
